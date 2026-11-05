"""Taller 2 · Generación: cabecera del documento (raíz, versión, número, fechas, tipo, moneda, leyenda)."""

import pytest
from lxml import etree

from src.adapters.outbound.ubl import NAMESPACES
from tests.unit.generacion_xml import fabrica as f


@pytest.mark.parametrize(("escenario", "raiz"), [
    ("factura-contado", "Invoice"), ("boleta", "Invoice"),
    ("nota-credito", "CreditNote"), ("nota-debito", "DebitNote"),
])
def test_el_tipo_de_comprobante_del_dominio_elige_el_documento_ubl(escenario, raiz):
    xml = f.arbol(f.ESCENARIOS[escenario]())
    assert etree.QName(xml).localname == raiz
    assert etree.QName(xml).namespace == NAMESPACES[raiz]


def test_declaracion_xml_utf8():
    assert f.generar(f.factura_contado()).startswith(b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>")


def test_version_ubl_y_personalizacion_sunat():
    xml = f.arbol(f.factura_contado())
    assert f.texto(xml, "cbc:UBLVersionID") == "2.1"
    assert f.texto(xml, "cbc:CustomizationID") == "2.0"
    assert f.texto(xml, "cbc:CustomizationID/@schemeAgencyName") == "PE:SUNAT"


def test_cbc_id_une_serie_y_correlativo_solo_al_serializar():
    xml = f.arbol(f.armar(f.TipoComprobante.FACTURA, "FA01", (f.linea(1),), correlativo=12_345_678))
    assert f.texto(xml, "cbc:ID") == "FA01-12345678"


def test_fecha_y_hora_de_emision():
    xml = f.arbol(f.factura_contado())
    assert (f.texto(xml, "cbc:IssueDate"), f.texto(xml, "cbc:IssueTime")) == ("2026-10-22", "10:30:00")


@pytest.mark.parametrize(("escenario", "codigo", "operacion"), [
    ("factura-contado", "01", "0101"), ("boleta", "03", "0101"), ("factura-exportacion-usd", "01", "0200"),
])
def test_invoice_type_code_catalogo_01_y_tipo_de_operacion_catalogo_51(escenario, codigo, operacion):
    xml = f.arbol(f.ESCENARIOS[escenario]())
    assert f.texto(xml, "cbc:InvoiceTypeCode") == codigo
    assert f.texto(xml, "cbc:InvoiceTypeCode/@listID") == operacion
    assert f.texto(xml, "cbc:InvoiceTypeCode/@listURI").endswith("catalogo01")


@pytest.mark.parametrize(("escenario", "moneda"), [("factura-contado", "PEN"), ("factura-exportacion-usd", "USD")])
def test_moneda_catalogo_02_en_el_documento_y_en_cada_importe(escenario, moneda):
    xml = f.arbol(f.ESCENARIOS[escenario]())
    assert f.texto(xml, "cbc:DocumentCurrencyCode") == moneda
    assert set(f.todos(xml, "//@currencyID")) == {moneda}


def test_leyenda_1000_importe_en_letras():
    xml = f.arbol(f.factura_credito())
    assert f.texto(xml, "cbc:Note[@languageLocaleID='1000']") == "DOSCIENTOS CUARENTA Y SIETE CON 80/100 SOLES"


def test_leyenda_en_dolares():
    xml = f.arbol(f.factura_exportacion_usd())
    assert f.texto(xml, "cbc:Note[@languageLocaleID='1000']").endswith("CON 00/100 DÓLARES AMERICANOS")


def test_el_xml_se_genera_sin_firma_la_agrega_el_adaptador_de_firma():
    xml = f.arbol(f.factura_contado())
    assert xml.find("ext:UBLExtensions", f.NS) is None
    assert f.texto(xml, "cac:Signature/cbc:ID") == "SignatureSP"
    assert f.texto(xml, "cac:Signature/cac:DigitalSignatureAttachment/cac:ExternalReference/cbc:URI") == \
        "#SignatureSP"
