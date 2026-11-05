"""La evidencia de ``docs/evidencia-sunat/`` es real y sigue correspondiendo al código.

``scripts/validar_en_sunat_beta.py`` envió los siete comprobantes de ejemplo al servicio
beta de SUNAT y guardó lo enviado y lo respondido. Esta prueba, sin red:

* vuelve a interpretar cada respuesta SOAP con el adaptador de producción (código 0);
* comprueba que cada CDR responde al comprobante enviado (serie, emisor y receptor);
* verifica la firma de cada XML enviado;
* regenera los comprobantes con el código actual y exige que sean idénticos a los que
  SUNAT aceptó (salvo firma y hora). Si un cambio altera el XML, esta prueba falla: hay
  que volver a ejecutar el script contra beta, no solo actualizar la prueba.
"""

from __future__ import annotations

import base64
import datetime as dt
import io
import json
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from signxml import XMLVerifier

from scripts.validar_en_sunat_beta import CABECERAS, COMPROBANTES, DESTINO, FICHAS, _cargar
from src.adapters.inbound.http.app import crear_app
from src.adapters.outbound.ose.sunat_soap import ClienteSunatSoap, RespuestaHttp
from src.adapters.outbound.reloj import ZONA_PERU, RelojFijo
from src.bootstrap import construir_contenedor
from src.config import Configuracion
from src.domain.comprobante import EstadoComprobante

ENVIADOS = DESTINO / "enviados"
RESPUESTAS = DESTINO / "respuestas"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
RESULTADO = json.loads((DESTINO / "resultado.json").read_text(encoding="utf-8"))
NOMBRES = [r["comprobante"] for r in RESULTADO]


def _cdr(nombre: str) -> etree._Element:
    sobre = (RESPUESTAS / f"{nombre}.soap.xml").read_bytes()
    contenido = base64.b64decode(re.search(rb"<applicationResponse>(.*?)</applicationResponse>", sobre, re.S).group(1))
    with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
        return etree.fromstring(archivo.read(f"R-{nombre}.xml"))


def _sin_firma_ni_hora(xml: bytes) -> bytes:
    raiz = etree.fromstring(xml)
    for nodo in [*raiz.iter(f"{{{EXT}}}UBLExtensions"), *raiz.iter(f"{{{CBC}}}IssueTime")]:
        nodo.getparent().remove(nodo)
    return etree.tostring(raiz, method="c14n")


def test_estan_los_siete_comprobantes_del_caso():
    assert len(RESULTADO) == len(COMPROBANTES) == 7
    assert sorted(p.stem for p in ENVIADOS.glob("*.xml")) == sorted(NOMBRES)
    assert sorted(p.name.removesuffix(".soap.xml") for p in RESPUESTAS.glob("*.xml")) == sorted(NOMBRES)


@pytest.mark.parametrize("nombre", NOMBRES)
def test_sunat_acepto_cada_comprobante(nombre, reloj):
    ose = ClienteSunatSoap(ruc=nombre.split("-")[0], reloj=reloj, transporte=lambda *_: None)  # type: ignore[arg-type]
    cdr = ose.interpretar(RespuestaHttp(200, (RESPUESTAS / f"{nombre}.soap.xml").read_bytes()))
    assert (cdr.codigo, cdr.estado_resultante) == ("0", EstadoComprobante.ACEPTADO)


@pytest.mark.parametrize("nombre", NOMBRES)
def test_cada_cdr_responde_al_comprobante_enviado(nombre):
    ruc, _, serie_numero = nombre.split("-", 2)
    cdr = _cdr(nombre)
    assert cdr.findtext(f".//{{{CBC}}}ReferenceID") == serie_numero
    assert cdr.find(".//{*}ReceiverParty").findtext(".//{*}ID") == ruc
    assert cdr.find(".//{*}SenderParty").findtext(".//{*}ID") == "20131312955"  # RUC de SUNAT
    enviado = etree.parse(str(ENVIADOS / f"{nombre}.xml")).getroot()
    cliente = enviado.find(".//{*}AccountingCustomerParty//{*}PartyIdentification/{*}ID")
    # Beta escribe "6-" como tipo de documento aun para un DNI (B001-1): se compara el número.
    assert cdr.find(".//{*}RecipientParty").findtext(".//{*}ID").split("-", 1)[1] == cliente.text


@pytest.mark.parametrize("nombre", NOMBRES)
def test_la_firma_de_lo_enviado_es_valida(nombre):
    raiz = etree.parse(str(ENVIADOS / f"{nombre}.xml")).getroot()
    certificado = raiz.findtext(".//{http://www.w3.org/2000/09/xmldsig#}X509Certificate").strip()
    pem = f"-----BEGIN CERTIFICATE-----\n{certificado}\n-----END CERTIFICATE-----\n"
    XMLVerifier().verify(raiz, x509_cert=pem, expect_references=1)


def test_el_codigo_actual_genera_lo_que_sunat_acepto():
    primero = etree.parse(str(ENVIADOS / f"{NOMBRES[0]}.xml")).getroot()
    fecha = dt.date.fromisoformat(primero.findtext(f"{{{CBC}}}IssueDate"))
    reloj = RelojFijo(dt.datetime.combine(fecha, dt.time(10, 30), tzinfo=ZONA_PERU))
    contenedor = construir_contenedor(Configuracion(), reloj=reloj)
    cliente = TestClient(crear_app(contenedor))
    for ficha in FICHAS:
        cliente.post("/api/v1/inventario/migraciones", json=_cargar(ficha), headers=CABECERAS).raise_for_status()
    distintos = []
    for ejemplo, nombre in zip(COMPROBANTES, NOMBRES, strict=True):
        r = cliente.post("/api/v1/comprobantes", json=_cargar(ejemplo), headers=CABECERAS).json()
        xml = cliente.get(f"/api/v1/comprobantes/{r['tipo_comprobante']['codigo']}/{r['serie_numero']}/xml",
                          headers=CABECERAS).content
        if _sin_firma_ni_hora(xml) != _sin_firma_ni_hora((ENVIADOS / f"{nombre}.xml").read_bytes()):
            distintos.append(nombre)
    contenedor.cerrar()
    assert distintos == [], "el XML cambió: ejecute python scripts/validar_en_sunat_beta.py y versione la evidencia"


def test_la_evidencia_no_incluye_claves_privadas():
    for archivo in Path(DESTINO).rglob("*"):
        if archivo.is_file():
            assert b"PRIVATE KEY" not in archivo.read_bytes(), archivo
