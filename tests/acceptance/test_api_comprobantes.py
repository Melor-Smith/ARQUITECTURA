"""Aceptación HTTP de comprobantes. Cada clase responde a una observación de la revisión."""

from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from src.adapters.inbound.http.app import crear_app
from src.adapters.outbound.ose.simulada import ModoOse
from src.bootstrap import construir_contenedor
from src.config import Configuracion
from src.domain.valores import digito_verificador_ruc
from tests.conftest import CONSULTA, FACTURADOR, URL_COMPROBANTES, ejemplo

PROBLEMA = "application/problem+json"


def problema(respuesta, status: int, codigo: str | None = None) -> dict:
    assert respuesta.status_code == status, respuesta.text
    assert respuesta.headers["content-type"].startswith(PROBLEMA)
    cuerpo = respuesta.json()
    assert cuerpo["status"] == status
    if codigo:
        assert cuerpo["codigo"] == codigo, cuerpo
    return cuerpo


class TestEmisionFeliz:
    def test_factura_201_con_estado_del_cdr_y_location(self, emitir):
        r = emitir(ejemplo("factura.json"))
        assert r.status_code == 201
        cuerpo = r.json()
        assert cuerpo["serie_numero"] == "F001-1"
        assert (cuerpo["serie"], cuerpo["correlativo"]) == ("F001", 1)
        assert cuerpo["estado"] == "ACEPTADO"
        assert cuerpo["cdr"]["codigo"] == "0"
        assert r.headers["location"] == f"{URL_COMPROBANTES}/01/F001-1"

    def test_los_impuestos_y_totales_los_calcula_el_servidor(self, emitir):
        cuerpo = emitir(ejemplo("factura.json")).json()
        assert cuerpo["totales"] == {
            "gravadas": "305.00", "exoneradas": "0.00", "inafectas": "0.00", "exportacion": "0.00",
            "isc": "0.00", "igv": "54.90", "icbper": "0.00", "total_impuestos": "54.90",
            "valor_venta": "305.00", "importe_total": "359.90",
        }

    def test_isc_de_los_tres_sistemas_e_icbper(self, emitir):
        cuerpo = emitir(ejemplo("factura-isc-icbper.json")).json()
        isc = [ln["isc"] for ln in cuerpo["lineas"]]
        assert [i["sistema"]["codigo"] for i in isc[:3]] == ["01", "02", "03"]
        assert [i["monto"] for i in isc[:3]] == ["54.00", "16.20", "7.20"]
        assert cuerpo["lineas"][3]["icbper"] == "1.50"
        assert D(cuerpo["totales"]["importe_total"]) == sum(
            D(cuerpo["totales"][k]) for k in ("valor_venta", "isc", "igv", "icbper"))

    def test_hash_cpe_es_el_digest_value_del_xml_firmado(self, emitir, cliente):
        cuerpo = emitir(ejemplo("factura.json")).json()
        xml = cliente.get(cuerpo["enlaces"]["xml"], headers=CONSULTA)
        assert xml.headers["content-type"].startswith("application/xml")
        digest = etree.fromstring(xml.content).find(".//{http://www.w3.org/2000/09/xmldsig#}DigestValue").text
        assert cuerpo["hash_cpe"] == digest


class TestSerieYCorrelativo:
    def test_boleta_b001_es_aceptada(self, emitir):
        r = emitir(ejemplo("boleta.json"))
        assert (r.status_code, r.json()["serie_numero"]) == (201, "B001-1")

    def test_serie_alfanumerica_fa01(self, emitir):
        assert emitir(ejemplo("factura-isc-icbper.json")).json()["serie_numero"] == "FA01-1"

    def test_correlativo_legal_de_8_digitos(self, reloj):
        contenedor = construir_contenedor(Configuracion(), reloj=reloj,
                                          ultimos_correlativos={("01", "F001"): 12_345_677})
        cliente = TestClient(crear_app(contenedor))
        r = cliente.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=FACTURADOR)
        assert r.json()["serie_numero"] == "F001-12345678"
        assert cliente.get(f"{URL_COMPROBANTES}/01/F001-12345678", headers=CONSULTA).status_code == 200

    def test_ceros_a_la_izquierda_en_la_consulta(self, emitir, cliente):
        emitir(ejemplo("factura.json"))
        assert cliente.get(f"{URL_COMPROBANTES}/01/F001-00000001", headers=CONSULTA).json()["serie_numero"] == "F001-1"

    def test_el_correlativo_lo_asigna_el_servidor_y_no_el_cliente(self, emitir):
        payload = ejemplo("factura.json") | {"correlativo": 99}
        problema(emitir(payload), 400, "ERR-CONTRATO-CAMPO-NO-PERMITIDO")

    def test_dos_emisiones_no_se_sobrescriben(self, emitir):
        assert [emitir(ejemplo("factura.json")).json()["serie_numero"] for _ in range(2)] == ["F001-1", "F001-2"]

    def test_nueve_digitos_es_formato_invalido(self, cliente):
        problema(cliente.get(f"{URL_COMPROBANTES}/01/F001-123456789", headers=CONSULTA), 400)

    def test_factura_con_serie_b_es_regla_de_negocio_422(self, emitir):
        problema(emitir(ejemplo("factura.json") | {"serie": "B001"}), 422, "ERR-SUNAT-SERIE")

    def test_boleta_con_serie_f_es_regla_de_negocio_422(self, emitir):
        problema(emitir(ejemplo("boleta.json") | {"serie": "F001"}), 422, "ERR-SUNAT-SERIE")

    def test_rechazo_de_negocio_no_consume_correlativo(self, emitir):
        problema(emitir(ejemplo("factura.json") | {"serie": "B001"}), 422)
        payload = ejemplo("factura.json")
        payload["lineas"][0]["cantidad"] = "999999"  # saldo insuficiente
        problema(emitir(payload), 422, "ERR-KARDEX-SALDO-INSUFICIENTE")
        assert emitir(ejemplo("factura.json")).json()["serie_numero"] == "F001-1"


class TestUnidadesUnece:
    def test_saco_de_50_kg_facturado_en_kgm(self, emitir, cliente):
        cuerpo = emitir(ejemplo("factura.json")).json()
        assert cuerpo["lineas"][0]["unidad_medida"] == "KGM"
        xml = cliente.get(cuerpo["enlaces"]["xml"], headers=CONSULTA).content
        assert b'unitCode="KGM"' in xml

    def test_unidad_fuera_del_catalogo_03(self, emitir):
        payload = ejemplo("factura.json")
        payload["lineas"][0]["unidad_medida"] = "SACO"
        problema(emitir(payload), 400, "ERR-SUNAT-CAT03")

    def test_unidad_distinta_a_la_del_producto(self, emitir):
        payload = ejemplo("factura.json")
        payload["lineas"][0]["unidad_medida"] = "NIU"
        problema(emitir(payload), 422, "ERR-SUNAT-CAT03")


class TestXml:
    def test_descripcion_con_ampersand_genera_xml_bien_formado(self, emitir, cliente):
        payload = ejemplo("factura.json")
        payload["lineas"][0]["descripcion"] = "Arroz & Azúcar"
        cuerpo = emitir(payload).json()
        xml = cliente.get(cuerpo["enlaces"]["xml"], headers=CONSULTA).content
        assert b"Arroz &amp; Az" in xml
        etree.fromstring(xml)


class TestCalculoDelegadoAlCliente:
    def test_el_cliente_no_puede_enviar_impuestos_ni_totales(self, emitir):
        payload = ejemplo("factura.json")
        payload["lineas"][0]["igv_item"] = 999
        payload["totales"] = {"importe_total": 1.00}
        cuerpo = problema(emitir(payload), 400, "ERR-CONTRATO-CAMPO-NO-PERMITIDO")
        assert {e["campo"] for e in cuerpo["errores"]} == {"lineas.0.igv_item", "totales"}


class TestValidacionesSunat:
    def test_ruc_con_digito_verificador_incorrecto(self, emitir):
        payload = ejemplo("factura.json")
        payload["cliente"]["numero_documento"] = "20123456780"
        problema(emitir(payload), 422, "ERR-SUNAT-RUC")

    @pytest.mark.parametrize("prefijo", ["15", "16", "17"])
    def test_prefijos_15_16_17_aceptados(self, emitir, prefijo):
        payload = ejemplo("factura.json")
        base = prefijo + "12345678"
        payload["cliente"]["numero_documento"] = base + str(digito_verificador_ruc(base))
        assert emitir(payload).status_code == 201

    def test_factura_a_cliente_con_dni(self, emitir):
        payload = ejemplo("factura.json")
        payload["cliente"] |= {"tipo_documento": "1", "numero_documento": "46027897"}
        problema(emitir(payload), 422, "ERR-SUNAT-RUC")

    def test_catalogo_08_codigo_inexistente(self, emitir):
        payload = ejemplo("factura-isc-icbper.json")
        payload["lineas"][0]["isc"]["sistema"] = "99"
        problema(emitir(payload), 400, "ERR-SUNAT-CAT08")

    def test_catalogo_08_configuracion_incompleta(self, emitir):
        payload = ejemplo("factura-isc-icbper.json")
        payload["lineas"][0]["isc"] = {"sistema": "01"}
        problema(emitir(payload), 422, "ERR-SUNAT-CAT08")

    def test_json_mal_formado(self, cliente):
        cabeceras = FACTURADOR | {"content-type": "application/json"}
        problema(cliente.post(URL_COMPROBANTES, content=b"{no es json", headers=cabeceras), 400)


class TestIdempotencia:
    def test_misma_clave_y_mismo_contenido_devuelve_el_original_sin_duplicar(self, cliente):
        cabeceras = FACTURADOR | {"Idempotency-Key": "pedido-2026-0001"}
        primera = cliente.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=cabeceras)
        segunda = cliente.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=cabeceras)
        assert (primera.status_code, segunda.status_code) == (201, 200)
        assert primera.json()["serie_numero"] == segunda.json()["serie_numero"] == "F001-1"
        tercera = cliente.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=FACTURADOR)
        assert tercera.json()["serie_numero"] == "F001-2"

    def test_misma_clave_con_otro_contenido_es_409(self, cliente):
        cabeceras = FACTURADOR | {"Idempotency-Key": "pedido-2026-0002"}
        cliente.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=cabeceras)
        otro = ejemplo("factura.json")
        otro["lineas"][0]["cantidad"] = "10"
        problema(cliente.post(URL_COMPROBANTES, json=otro, headers=cabeceras), 409, "ERR-IDEMPOTENCIA-CONFLICTO")


class TestSeguridad:
    def test_sin_token_401_con_www_authenticate(self, cliente):
        r = cliente.post(URL_COMPROBANTES, json=ejemplo("factura.json"))
        problema(r, 401, "ERR-AUTH-TOKEN")
        assert r.headers["www-authenticate"].startswith("Bearer")

    def test_token_desconocido_401(self, emitir):
        problema(emitir(ejemplo("factura.json"), {"Authorization": "Bearer inventado"}), 401)

    def test_token_sin_alcance_403(self, emitir):
        problema(emitir(ejemplo("factura.json"), CONSULTA), 403, "ERR-AUTH-ALCANCE")


class TestOse:
    def test_ose_caida_202_pendiente_y_luego_reenvio(self, emitir, cliente, contenedor):
        contenedor.ose.modo = ModoOse.CAIDA
        r = emitir(ejemplo("factura.json"))
        assert (r.status_code, r.json()["estado"], r.json()["cdr"]) == (202, "PENDIENTE_ENVIO", None)
        envios = r.json()["enlaces"]["envios"]

        reintento = cliente.post(envios, headers=FACTURADOR)
        problema(reintento, 503, "ERR-OSE-NO-DISPONIBLE")
        assert reintento.headers["retry-after"] == "120"

        contenedor.ose.modo = ModoOse.NORMAL
        aceptado = cliente.post(envios, headers=FACTURADOR)
        assert (aceptado.status_code, aceptado.json()["estado"], aceptado.json()["intentos_envio"]) == (
            200, "ACEPTADO", 3)
        problema(cliente.post(envios, headers=FACTURADOR), 409, "ERR-COMPROBANTE-YA-PROCESADO")

    def test_respuesta_invalida_de_la_ose_es_502_en_el_reenvio(self, emitir, cliente, contenedor):
        contenedor.ose.modo = ModoOse.RESPUESTA_INVALIDA
        r = emitir(ejemplo("factura.json"))
        assert r.status_code == 202
        problema(cliente.post(r.json()["enlaces"]["envios"], headers=FACTURADOR), 502, "ERR-OSE-RESPUESTA-INVALIDA")

    def test_rechazo_de_la_ose_se_refleja_y_revierte_el_kardex(self, emitir, cliente, contenedor):
        saldo_inicial = cliente.get("/api/v1/inventario/kardex/AB-ARR-001", headers=CONSULTA).json()["saldo_final"]
        contenedor.ose.modo = ModoOse.RECHAZO
        r = emitir(ejemplo("factura.json"))
        assert (r.status_code, r.json()["estado"], r.json()["cdr"]["codigo"]) == (201, "RECHAZADO", "2335")
        kardex = cliente.get("/api/v1/inventario/kardex/AB-ARR-001", headers=CONSULTA).json()
        assert kardex["saldo_final"] == saldo_inicial
        assert kardex["movimientos"][-1]["glosa"].startswith("Reversión")


class TestConsulta:
    def test_404_en_problem_json(self, cliente):
        problema(cliente.get(f"{URL_COMPROBANTES}/01/F999-1", headers=CONSULTA), 404, "ERR-COMPROBANTE-NO-ENCONTRADO")

    def test_tipo_de_comprobante_inexistente(self, cliente):
        problema(cliente.get(f"{URL_COMPROBANTES}/99/F001-1", headers=CONSULTA), 400)


class TestNotas:
    def test_nota_de_credito_por_devolucion_reingresa_al_kardex(self, emitir, cliente):
        emitir(ejemplo("factura.json"))
        r = emitir(ejemplo("nota-credito.json"))
        assert (r.status_code, r.json()["serie_numero"], r.json()["motivo"]["codigo"]) == (201, "FC01-1", "07")
        ultimo = cliente.get("/api/v1/inventario/kardex/AB-ARR-001", headers=CONSULTA).json()["movimientos"][-1]
        assert (ultimo["tipo_operacion"]["codigo"], ultimo["entrada"]) == ("24", "10")

    def test_nota_de_debito(self, emitir):
        emitir(ejemplo("factura.json"))
        assert emitir(ejemplo("nota-debito.json")).status_code == 201

    def test_nota_de_credito_que_excede_el_comprobante(self, emitir):
        emitir(ejemplo("factura.json"))
        payload = ejemplo("nota-credito.json")
        payload["lineas"][0]["cantidad"] = "500"
        problema(emitir(payload), 422)

    def test_nota_que_referencia_un_comprobante_inexistente(self, emitir):
        problema(emitir(ejemplo("nota-credito.json")), 422, "ERR-REFERENCIA-NO-EXISTE")

    def test_motivo_fuera_del_catalogo_09(self, emitir):
        emitir(ejemplo("factura.json"))
        problema(emitir(ejemplo("nota-credito.json") | {"motivo": "99"}), 400, "ERR-SUNAT-MOTIVO-NOTA")
