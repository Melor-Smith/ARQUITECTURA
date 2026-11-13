"""Pruebas unitarias de generación del caso de estudio: una venta registrada → XML UBL 2.1.

Parten del comando que produce el formulario (``GenerarXmlVentaCmd``) y verifican el XML que sale
del caso de uso ``GenerarXmlVenta``, con los adaptadores reales de generación, validación y firma.
El caso de estudio es la venta de una motocicleta: valor 4 237.29 + IGV 762.71 = S/ 5 000.00.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal as D

import pytest
from lxml import etree
from signxml import XMLVerifier

from src.adapters.inbound.http.vistas.matriz_ubl import filas_aplicadas
from src.adapters.outbound.firma.xmldsig import CertificadoDigital, FirmaXmlDsig
from src.adapters.outbound.persistencia.memoria import SecuenciaCorrelativosEnMemoria
from src.adapters.outbound.persistencia.semillas import EMISOR_ABC
from src.adapters.outbound.reloj import ZONA_PERU, RelojFijo
from src.adapters.outbound.ubl.generador import GeneradorUblXsdata
from src.adapters.outbound.ubl.validador import ValidadorXsdLxml
from src.application.casos_uso.venta_xml import GenerarXmlVenta, XmlDeVenta
from src.application.comandos import ClienteCmd, GenerarXmlVentaCmd, LineaCmd
from src.domain.catalogos import AfectacionIGV, TipoComprobante, TipoDocumentoIdentidad, UnidadMedida
from src.domain.errores import ErrorDominio, ReglaComprobanteIncumplida
from tests.unit.generacion_xml.fabrica import NS

AHORA = dt.datetime(2026, 11, 12, 10, 15, tzinfo=ZONA_PERU)
VALIDADOR = ValidadorXsdLxml()
CLIENTE_RUC = ClienteCmd(TipoDocumentoIdentidad.RUC, "20123456786", "DISTRIBUIDORA DE ABARROTES EL SOL S.A.C.",
                         "JR. COMERCIO 123, LIMA")
CLIENTE_DNI = ClienteCmd(TipoDocumentoIdentidad.DNI, "46027897", "MARÍA QUISPE HUAMÁN")
SIN_DOCUMENTO = ClienteCmd(TipoDocumentoIdentidad.NO_DOMICILIADO, "-", "CLIENTE VARIOS")


def moto(valor: str = "4237.29", cantidad: str = "1",
         afectacion: AfectacionIGV = AfectacionIGV.GRAVADO_ONEROSA) -> LineaCmd:
    return LineaCmd("Motocicleta 150 cc para reparto", UnidadMedida.UNIDAD, D(cantidad), D(valor), afectacion)


CERTIFICADO = CertificadoDigital.autofirmado_para_desarrollo(str(EMISOR_ABC.ruc), EMISOR_ABC.razon_social)


@pytest.fixture(scope="module")
def firma() -> FirmaXmlDsig:
    return FirmaXmlDsig(CERTIFICADO)


@pytest.fixture
def generar(firma):
    caso = GenerarXmlVenta(  # la misma configuración que bootstrap.py usa para el formulario /venta
        emisor=EMISOR_ABC, plazo_envio_dias=3, reloj=RelojFijo(AHORA), secuencia=SecuenciaCorrelativosEnMemoria(),
        generador_ubl=GeneradorUblXsdata(sangria="  ", declarar_prefijos_de_firma=True),
        validador_xsd=VALIDADOR, firma=firma,
    )

    def _generar(*lineas: LineaCmd, tipo=TipoComprobante.FACTURA, serie="FM0T", cliente=CLIENTE_RUC,
                 firmar=False) -> XmlDeVenta:
        return caso.ejecutar(GenerarXmlVentaCmd(tipo, serie, cliente, lineas or (moto(),), incluir_firma=firmar))

    return _generar


def raiz(resultado: XmlDeVenta) -> etree._Element:
    return etree.fromstring(resultado.xml)


def texto(resultado: XmlDeVenta, xpath: str) -> list[str]:
    return [str(v) if not isinstance(v, etree._Element) else (v.text or "") for v in
            raiz(resultado).xpath(xpath, namespaces={**NS, "inv": "urn:oasis:names:specification:ubl:schema:xsd:"
                                                                         "Invoice-2"})]


# --- el caso de estudio: la motocicleta --------------------------------------------------
def test_la_moto_genera_valor_de_venta_igv_y_total_calculados_por_el_dominio(generar):
    r = generar()
    assert texto(r, "/inv:Invoice/cac:InvoiceLine/cbc:LineExtensionAmount") == ["4237.29"]
    assert texto(r, "/inv:Invoice/cac:InvoiceLine/cac:TaxTotal/cbc:TaxAmount") == ["762.71"]
    assert texto(r, "/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount") == ["4237.29"]
    assert texto(r, "/inv:Invoice/cac:TaxTotal/cbc:TaxAmount") == ["762.71"]
    assert texto(r, "/inv:Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount") == ["5000.00"]
    assert texto(r, "/inv:Invoice/cbc:Note[@languageLocaleID='1000']") == ["CINCO MIL CON 00/100 SOLES"]


def test_la_moto_es_un_bien_por_unidad_gravado_con_igv(generar):
    r = generar()
    assert texto(r, "//cac:InvoiceLine/cbc:InvoicedQuantity/@unitCode") == ["NIU"]
    assert texto(r, "//cac:InvoiceLine//cbc:TaxExemptionReasonCode") == ["10"]  # Cat. 07: gravado onerosa
    assert texto(r, "//cac:InvoiceLine//cac:TaxScheme/cbc:ID") == ["1000"]  # Cat. 05: IGV
    assert texto(r, "//cac:InvoiceLine//cbc:Percent") == ["18.00"]
    assert texto(r, "//cac:InvoiceLine/cac:PricingReference//cbc:PriceAmount") == ["5000.00"]  # Cat. 16, tipo 01
    assert texto(r, "//cac:InvoiceLine/cac:Price/cbc:PriceAmount") == ["4237.29"]


def test_el_producto_es_libre_no_tiene_que_existir_en_el_catalogo_ni_tener_stock(generar):
    r = generar()
    assert texto(r, "//cac:Item/cbc:Description") == ["Motocicleta 150 cc para reparto"]
    assert texto(r, "//cac:Item/cac:SellersItemIdentification/cbc:ID") == []


def test_factura_de_venta_interna_al_contado_con_fecha_y_hora_del_dia(generar):
    r = generar()
    assert texto(r, "/inv:Invoice/cbc:InvoiceTypeCode") == ["01"]
    assert texto(r, "/inv:Invoice/cbc:InvoiceTypeCode/@listID") == ["0101"]  # Cat. 51
    assert texto(r, "/inv:Invoice/cbc:IssueDate") == ["2026-11-12"]
    assert texto(r, "/inv:Invoice/cbc:IssueTime") == ["10:15:00"]
    assert texto(r, "/inv:Invoice/cac:PaymentTerms/cbc:PaymentMeansID") == ["Contado"]  # RS 193-2020


# --- sin firma por defecto ----------------------------------------------------------------
def test_por_defecto_el_xml_sale_sin_firma_y_sin_ext_ublextensions(generar):
    r = generar()
    assert r.firmado is False
    assert raiz(r).find("ext:UBLExtensions", NS) is None
    assert raiz(r).find(".//ds:Signature", NS) is None


def test_el_xml_sin_firma_valida_contra_el_xsd_oficial(generar):
    VALIDADOR.validar(generar().xml, TipoComprobante.FACTURA)  # no lanza


def test_sin_firma_conserva_la_referencia_cac_signature_que_pide_sunat(generar):
    assert texto(generar(), "/inv:Invoice/cac:Signature/cbc:ID") == ["SignatureSP"]


def test_con_la_casilla_de_firma_el_xml_lleva_xmldsig_y_sigue_siendo_valido(generar):
    r = generar(firmar=True)
    assert r.firmado is True
    assert raiz(r).find("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/ds:Signature", NS) is not None
    VALIDADOR.validar(r.xml, TipoComprobante.FACTURA)


def test_no_hay_comentarios_ni_instrucciones_antes_del_elemento_raiz(generar):
    """probar-xml.nubefact.com falla si encuentra un comentario antes de <Invoice>."""
    xml = generar().xml.decode("utf-8")
    assert re.match(r'<\?xml version="1\.0" encoding="UTF-8"\?>\s*<Invoice\b', xml)
    assert "<!--" not in xml


def test_el_xml_del_formulario_sale_indentado_un_elemento_por_linea(generar):
    lineas = generar().xml.decode("utf-8").splitlines()
    assert len(lineas) > 50
    assert lineas[1].startswith("<Invoice ")
    assert "  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>" in lineas
    assert "    <cbc:LineExtensionAmount currencyID=\"PEN\">4237.29</cbc:LineExtensionAmount>" in lineas


def test_la_raiz_declara_ext_y_ds_para_que_quien_firme_despues_pueda_insertar_la_firma(generar):
    """Sin esto, el OSE-DEMO de Nubefact (casilla "Firmar") responde 0306: prefix "ext" is not bound."""
    raiz_sin_firma = raiz(generar())
    assert raiz_sin_firma.nsmap["ext"] == "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    assert raiz_sin_firma.nsmap["ds"] == "http://www.w3.org/2000/09/xmldsig#"
    assert raiz_sin_firma.find("ext:UBLExtensions", NS) is None  # declarados, pero todavía sin firma


def test_el_xml_indentado_y_firmado_conserva_una_firma_valida(generar):
    raiz_firmada = etree.fromstring(generar(firmar=True).xml)
    XMLVerifier().verify(raiz_firmada, x509_cert=CERTIFICADO.certificado_pem.decode(), expect_references=1)


def test_la_emision_por_la_api_sigue_generando_el_xml_compacto():
    """Los XML de referencia y la evidencia de SUNAT se comparan byte a byte: no se indentan."""
    from tests.unit.generacion_xml.fabrica import factura_contado

    compacto = GeneradorUblXsdata().generar(factura_contado())
    assert len(compacto.splitlines()) == 2
    assert b"xmlns:ext" not in compacto and b"xmlns:ds" not in compacto


# --- numeración y archivo -------------------------------------------------------------------
def test_el_correlativo_lo_asigna_el_sistema_y_avanza_en_la_misma_serie(generar):
    assert [generar().comprobante.serie_numero for _ in range(2)] == ["FM0T-1", "FM0T-2"]


def test_la_serie_se_normaliza_a_mayusculas(generar):
    assert texto(generar(serie=" fm0t "), "/inv:Invoice/cbc:ID") == ["FM0T-1"]


def test_el_archivo_lleva_el_nombre_sunat_ruc_tipo_serie_numero(generar):
    assert generar().nombre_archivo == "20556677884-01-FM0T-1.xml"


# --- boleta y reglas SUNAT del dominio -----------------------------------------------------
def test_boleta_de_la_moto_a_una_persona_con_dni(generar):
    r = generar(tipo=TipoComprobante.BOLETA, serie="BM0T", cliente=CLIENTE_DNI)
    assert texto(r, "/inv:Invoice/cbc:InvoiceTypeCode") == ["03"]
    assert texto(r, "//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID/@schemeID") == ["1"]
    assert texto(r, "/inv:Invoice/cac:PaymentTerms") == []  # la forma de pago se exige en facturas
    VALIDADOR.validar(r.xml, TipoComprobante.BOLETA)


def test_boleta_de_mas_de_700_soles_sin_identificar_al_cliente_se_rechaza(generar):
    with pytest.raises(ReglaComprobanteIncumplida, match="700"):
        generar(tipo=TipoComprobante.BOLETA, serie="BM0T", cliente=SIN_DOCUMENTO)


def test_boleta_pequena_sin_identificar_al_cliente_si_se_genera(generar):
    r = generar(moto("50.00"), tipo=TipoComprobante.BOLETA, serie="BM0T", cliente=SIN_DOCUMENTO)
    assert texto(r, "/inv:Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount") == ["59.00"]


def test_factura_a_un_cliente_con_dni_se_rechaza(generar):
    with pytest.raises(ErrorDominio) as error:
        generar(cliente=CLIENTE_DNI)
    assert error.value.codigo == "ERR-SUNAT-RUC"


def test_la_serie_debe_corresponder_al_tipo_de_comprobante(generar):
    with pytest.raises(ErrorDominio) as error:
        generar(serie="BM0T")
    assert error.value.codigo == "ERR-SUNAT-SERIE"


def test_las_notas_no_se_generan_desde_el_formulario_de_venta(generar):
    with pytest.raises(ReglaComprobanteIncumplida, match="facturas"):
        generar(tipo=TipoComprobante.NOTA_CREDITO)


def test_venta_con_productos_gravados_y_exonerados(generar):
    r = generar(moto(), LineaCmd("Casco certificado", UnidadMedida.UNIDAD, D("2"), D("80.00"),
                                 AfectacionIGV.EXONERADO_ONEROSA))
    assert texto(r, "//cac:InvoiceLine/cbc:ID") == ["1", "2"]
    assert texto(r, "/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID") == [
        "1000", "9997"]
    assert texto(r, "/inv:Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount") == ["5160.00"]


# --- la matriz del formulario ---------------------------------------------------------------
def test_la_matriz_muestra_el_valor_que_quedo_en_cada_etiqueta_ubl(generar):
    filas = {f.id: f for f in filas_aplicadas(generar().xml)}
    assert filas["T03"].valor == "FM0T-1"
    assert filas["T03"].xpath == "/Invoice/cbc:ID"
    assert filas["T62"].valor == "5000.00"
    assert filas["T40"].valor == "10"
    assert filas["T03"].obligatorio


def test_la_matriz_solo_incluye_la_firma_cuando_el_xml_esta_firmado(generar):
    assert "T80" not in {f.id for f in filas_aplicadas(generar().xml)}
    assert "T80" in {f.id for f in filas_aplicadas(generar(firmar=True).xml)}


def test_sin_el_archivo_de_la_matriz_el_panel_queda_vacio(generar, tmp_path):
    assert filas_aplicadas(generar().xml, tmp_path / "no-existe.csv") == []
