"""Adaptador SOAP de SUNAT probado con respuestas REALES del servicio beta.

Los archivos de ``tests/fixtures/sunat_beta/`` son respuestas literales de
``e-beta.sunat.gob.pe`` capturadas el 05/11/2026: una aceptación (CDR código 0), un rechazo
(2335, firma alterada) y una excepción (0161, nombre del ZIP). El transporte HTTP se
reemplaza por uno que las devuelve, así la CI no depende de la red ni de la disponibilidad
de SUNAT. La prueba contra el servicio en vivo está en ``test_sunat_beta_en_vivo.py``.
"""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from src.adapters.inbound.http.app import crear_app
from src.adapters.outbound.ose.sunat_soap import (
    ENDPOINT_BETA,
    ENDPOINT_PRODUCCION,
    ClienteSunatSoap,
    RespuestaHttp,
)
from src.application.errores import OseNoDisponible, OseRespuestaInvalida
from src.bootstrap import construir_contenedor
from src.config import Configuracion
from src.domain.comprobante import EstadoComprobante
from src.domain.errores import ErrorDominio
from tests.conftest import FACTURADOR, ejemplo

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sunat_beta"
RUC = "20556677884"
NOMBRE = f"{RUC}-01-F001-1"


def _fixture(nombre: str) -> RespuestaHttp:
    archivo = FIXTURES / nombre
    return RespuestaHttp(int(archivo.stem.rsplit(".http", 1)[1]), archivo.read_bytes())


class TransporteGrabado:
    """Devuelve una respuesta fija y guarda la solicitud para inspeccionarla."""

    def __init__(self, respuesta: RespuestaHttp | Exception) -> None:
        self.respuesta = respuesta
        self.solicitudes: list[tuple[str, bytes, dict[str, str]]] = []

    def __call__(self, url: str, cuerpo: bytes, cabeceras: dict[str, str], timeout: float) -> RespuestaHttp:
        self.solicitudes.append((url, cuerpo, cabeceras))
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


def _cliente(respuesta: RespuestaHttp | Exception, reloj) -> tuple[ClienteSunatSoap, TransporteGrabado]:
    transporte = TransporteGrabado(respuesta)
    return ClienteSunatSoap(ruc=RUC, reloj=reloj, transporte=transporte), transporte


def _sobre_con_cdr(cdr_xml: bytes) -> RespuestaHttp:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archivo:
        archivo.writestr(f"R-{NOMBRE}.xml", cdr_xml)
    contenido = base64.b64encode(buffer.getvalue()).decode()
    return RespuestaHttp(200, (
        '<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"><soap-env:Body>'
        f'<br:sendBillResponse xmlns:br="http://service.sunat.gob.pe"><applicationResponse>{contenido}'
        "</applicationResponse></br:sendBillResponse></soap-env:Body></soap-env:Envelope>").encode())


def _falla(faultcode: str, faultstring: str, estado: int = 500) -> RespuestaHttp:
    return RespuestaHttp(estado, (
        '<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"><soap-env:Body>'
        f"<soap-env:Fault><faultcode>{faultcode}</faultcode><faultstring>{faultstring}</faultstring>"
        "</soap-env:Fault></soap-env:Body></soap-env:Envelope>").encode())


class TestRespuestasRealesDeSunatBeta:
    def test_cdr_aceptado(self, reloj):
        ose, _ = _cliente(_fixture("aceptado-F001-1.http200.xml"), reloj)
        cdr = ose.enviar(NOMBRE, b"<Invoice/>")
        assert (cdr.codigo, cdr.descripcion) == ("0", "La Factura numero F001-1, ha sido aceptada")
        assert cdr.estado_resultante is EstadoComprobante.ACEPTADO
        assert cdr.fecha_recepcion == reloj.ahora()

    def test_firma_alterada_es_rechazo_2335(self, reloj):
        ose, _ = _cliente(_fixture("rechazo-2335-firma-alterada.http500.xml"), reloj)
        cdr = ose.enviar(NOMBRE, b"<Invoice/>")
        assert (cdr.codigo, cdr.descripcion) == ("2335", "El documento electrónico ingresado ha sido alterado")
        assert cdr.estado_resultante is EstadoComprobante.RECHAZADO

    def test_excepcion_0161_no_es_cdr_ni_reintentable(self, reloj):
        ose, _ = _cliente(_fixture("excepcion-0161-nombre-zip.http200.xml"), reloj)
        cdr = ose.enviar(NOMBRE, b"<Invoice/>")
        assert cdr.codigo == "0161"
        with pytest.raises(ErrorDominio, match="excepción"):
            cdr.estado_resultante  # noqa: B018 - el caso de uso lo convierte en 502


class TestSolicitud:
    def test_sobre_soap_segun_el_manual_del_programador(self, reloj):
        ose, transporte = _cliente(_fixture("aceptado-F001-1.http200.xml"), reloj)
        xml = "<Invoice>ñandú & cía</Invoice>".encode()
        ose.enviar(NOMBRE, xml)

        [(url, cuerpo, cabeceras)] = transporte.solicitudes
        assert url == ENDPOINT_BETA
        assert cabeceras["SOAPAction"] == "urn:sendBill"
        sobre = etree.fromstring(cuerpo)
        assert sobre.findtext(".//{*}Username") == f"{RUC}MODDATOS"
        assert sobre.findtext(".//{*}Password") == "moddatos"
        assert sobre.findtext(".//fileName") == f"{NOMBRE}.zip"
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(sobre.findtext(".//contentFile")))) as archivo:
            assert archivo.namelist() == [f"{NOMBRE}.xml"]  # 0161 si no coinciden
            assert archivo.read(f"{NOMBRE}.xml") == xml  # los bytes firmados, sin tocar

    def test_no_envia_comprobantes_de_otro_ruc(self, reloj):
        ose, transporte = _cliente(_fixture("aceptado-F001-1.http200.xml"), reloj)
        with pytest.raises(OseRespuestaInvalida, match="no pertenece"):
            ose.enviar("20100070970-01-F001-1", b"<Invoice/>")
        assert transporte.solicitudes == []


class TestTraduccionDeFallos:
    @pytest.mark.parametrize("codigo", ["0100", "0109", "0130", "0138", "0200"])
    def test_excepciones_de_servicio_son_reintentables(self, reloj, codigo):
        ose, _ = _cliente(_falla(f"soap-env:Server.{codigo}", "El sistema no puede responder su solicitud"), reloj)
        with pytest.raises(OseNoDisponible):
            ose.enviar(NOMBRE, b"<Invoice/>")

    @pytest.mark.parametrize("codigo", ["0102", "0111", "0151", "1033"])
    def test_otras_excepciones_llegan_al_dominio_con_su_codigo(self, reloj, codigo):
        ose, _ = _cliente(_falla(f"soap-env:Client.{codigo}", "Error"), reloj)
        assert ose.enviar(NOMBRE, b"<Invoice/>").codigo == codigo

    def test_codigo_en_faultstring_cuando_faultcode_no_lo_trae(self, reloj):
        ose, _ = _cliente(_falla("soap-env:Client", "3277 - La sumatoria no corresponde"), reloj)
        assert ose.enviar(NOMBRE, b"<Invoice/>").codigo == "3277"

    def test_falla_sin_codigo_es_respuesta_invalida(self, reloj):
        ose, _ = _cliente(_falla("soap-env:Server", "NullPointerException"), reloj)
        with pytest.raises(OseRespuestaInvalida):
            ose.enviar(NOMBRE, b"<Invoice/>")

    @pytest.mark.parametrize("estado", [401, 429, 502, 503])
    def test_html_del_balanceador_es_reintentable(self, reloj, estado):
        # Observado en beta: nginx responde "401 Authorization Required" ante ráfagas de envíos.
        ose, _ = _cliente(RespuestaHttp(estado, b"<html><head><title>401</title></head><body></html"), reloj)
        with pytest.raises(OseNoDisponible):
            ose.enviar(NOMBRE, b"<Invoice/>")

    def test_html_inesperado_es_respuesta_invalida(self, reloj):
        ose, _ = _cliente(RespuestaHttp(404, b"no encontrado"), reloj)
        with pytest.raises(OseRespuestaInvalida):
            ose.enviar(NOMBRE, b"<Invoice/>")

    @pytest.mark.parametrize("error", [TimeoutError("timed out"), ConnectionRefusedError("refused"), OSError("DNS")])
    def test_red_caida_es_reintentable(self, reloj, error):
        ose, _ = _cliente(error, reloj)
        with pytest.raises(OseNoDisponible):
            ose.enviar(NOMBRE, b"<Invoice/>")

    def test_sobre_sin_cdr_ni_falla(self, reloj):
        ose, _ = _cliente(RespuestaHttp(200, b"<Envelope><Body/></Envelope>"), reloj)
        with pytest.raises(OseRespuestaInvalida):
            ose.enviar(NOMBRE, b"<Invoice/>")

    @pytest.mark.parametrize("cdr", [b"no es xml", b'<ApplicationResponse xmlns="x"/>'])
    def test_cdr_ilegible_o_sin_codigo(self, reloj, cdr):
        ose, _ = _cliente(_sobre_con_cdr(cdr), reloj)
        with pytest.raises(OseRespuestaInvalida):
            ose.enviar(NOMBRE, b"<Invoice/>")

    def test_zip_corrupto(self, reloj):
        respuesta = RespuestaHttp(200, b'<E xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><applicationResponse>'
                                       + base64.b64encode(b"no es zip") + b"</applicationResponse></E>")
        ose, _ = _cliente(respuesta, reloj)
        with pytest.raises(OseRespuestaInvalida):
            ose.enviar(NOMBRE, b"<Invoice/>")

    def test_cdr_con_observaciones(self, reloj):
        cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        nota = "4252 - El dato ingresado como atributo @listName es incorrecto."
        cdr = (f'<ar:ApplicationResponse xmlns:ar="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"'
               f' xmlns:cbc="{cbc}"><cbc:Note>{nota}</cbc:Note>'
               f"<cbc:ResponseCode>0</cbc:ResponseCode><cbc:Description>aceptada</cbc:Description>"
               f"</ar:ApplicationResponse>").encode()
        ose, _ = _cliente(_sobre_con_cdr(cdr), reloj)
        resultado = ose.enviar(NOMBRE, b"<Invoice/>")
        assert resultado.observaciones == ("4252 - El dato ingresado como atributo @listName es incorrecto.",)
        assert resultado.estado_resultante is EstadoComprobante.ACEPTADO_CON_OBSERVACIONES


class TestDeExtremoAExtremo:
    """La API con el adaptador SUNAT en lugar de la OSE simulada: ningún caso de uso cambia."""

    @pytest.mark.parametrize(("fixture", "estado", "codigo"), [
        ("aceptado-F001-1.http200.xml", "ACEPTADO", "0"),
        ("rechazo-2335-firma-alterada.http500.xml", "RECHAZADO", "2335"),
    ])
    def test_emision_con_respuesta_real(self, reloj, fixture, estado, codigo):
        transporte = TransporteGrabado(_fixture(fixture))
        ose = ClienteSunatSoap(ruc=RUC, reloj=reloj, transporte=transporte)
        contenedor = construir_contenedor(Configuracion(), reloj=reloj, ose=ose)
        r = TestClient(crear_app(contenedor)).post("/api/v1/comprobantes", json=ejemplo("factura.json"),
                                                   headers=FACTURADOR)
        assert (r.status_code, r.json()["estado"], r.json()["cdr"]["codigo"]) == (201, estado, codigo)
        assert len(transporte.solicitudes) == 1

    def test_sunat_caida_deja_el_comprobante_pendiente(self, reloj):
        ose = ClienteSunatSoap(ruc=RUC, reloj=reloj, transporte=TransporteGrabado(TimeoutError()))
        contenedor = construir_contenedor(Configuracion(), reloj=reloj, ose=ose)
        r = TestClient(crear_app(contenedor)).post("/api/v1/comprobantes", json=ejemplo("factura.json"),
                                                   headers=FACTURADOR)
        assert (r.status_code, r.json()["estado"]) == (202, "PENDIENTE_ENVIO")


class TestConfiguracion:
    def test_beta_por_variable_de_entorno(self, monkeypatch, reloj):
        monkeypatch.setenv("ABC_SUNAT_ENDPOINT", "beta")
        configuracion = Configuracion.desde_entorno()
        assert configuracion.sunat_endpoint == ENDPOINT_BETA
        assert isinstance(construir_contenedor(configuracion, reloj=reloj).ose, ClienteSunatSoap)

    def test_sin_endpoint_se_usa_la_ose_simulada(self, monkeypatch, reloj):
        monkeypatch.delenv("ABC_SUNAT_ENDPOINT", raising=False)
        assert not isinstance(construir_contenedor(Configuracion.desde_entorno(), reloj=reloj).ose, ClienteSunatSoap)

    def test_produccion_exige_certificado_y_usuario_sol_reales(self, monkeypatch):
        monkeypatch.setenv("ABC_SUNAT_ENDPOINT", "produccion")
        with pytest.raises(ValueError, match="Producción SUNAT exige"):
            Configuracion.desde_entorno()
        assert Configuracion(sunat_endpoint=ENDPOINT_PRODUCCION, certificado_pfx=Path("c.pfx"),
                             sunat_usuario_sol="FACTURA1", tokens={"token-propio": frozenset({"libros:leer"})},
                             ).sunat_endpoint == ENDPOINT_PRODUCCION
