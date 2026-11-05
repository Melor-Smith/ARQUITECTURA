"""Taller 2 · Generación: totales, forma de pago, documentos relacionados y notas."""

from decimal import Decimal as D

from tests.unit.generacion_xml import fabrica as f


def test_totales_monetarios():
    xml = f.arbol(f.factura_contado())
    assert f.texto(xml, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount") == "210.00"
    assert f.texto(xml, "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount") == "247.80"
    assert f.texto(xml, "cac:LegalMonetaryTotal/cbc:PayableAmount") == "247.80"


def test_importe_total_es_valor_de_venta_mas_tributos():
    xml = f.arbol(f.factura_completa())
    venta = D(f.texto(xml, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount"))
    tributos = D(f.texto(xml, "cac:TaxTotal/cbc:TaxAmount"))
    assert D(f.texto(xml, "cac:LegalMonetaryTotal/cbc:PayableAmount")) == venta + tributos


def test_nota_de_debito_usa_requested_monetary_total():
    xml = f.arbol(f.nota_debito())
    assert f.texto(xml, "cac:RequestedMonetaryTotal/cbc:PayableAmount") == "17.70"
    assert not f.todos(xml, "cac:LegalMonetaryTotal")


def test_forma_de_pago_contado():
    xml = f.arbol(f.factura_contado())
    assert f.todos(xml, "cac:PaymentTerms/cbc:ID") == ["FormaPago"]
    assert f.todos(xml, "cac:PaymentTerms/cbc:PaymentMeansID") == ["Contado"]
    assert not f.todos(xml, "cac:PaymentTerms/cbc:Amount")


def test_forma_de_pago_credito_con_monto_pendiente_y_cuotas():
    xml = f.arbol(f.factura_credito())
    assert f.todos(xml, "cac:PaymentTerms/cbc:PaymentMeansID") == ["Credito", "Cuota001", "Cuota002"]
    assert f.texto(xml, "cac:PaymentTerms[cbc:PaymentMeansID='Credito']/cbc:Amount") == "247.80"
    assert f.todos(xml, "cac:PaymentTerms[starts-with(cbc:PaymentMeansID,'Cuota')]/cbc:Amount") == \
        ["123.90", "123.90"]
    assert f.todos(xml, "cac:PaymentTerms/cbc:PaymentDueDate") == ["2026-11-21", "2026-12-21"]


def test_boleta_y_notas_no_llevan_forma_de_pago():
    for escenario in (f.boleta, f.nota_credito, f.nota_debito):
        assert not f.todos(f.arbol(escenario()), "cac:PaymentTerms")


def test_vale_legado_como_documento_relacionado_catalogo_12_tipo_99():
    xml = f.arbol(f.factura_de_vale())
    assert f.texto(xml, "cac:AdditionalDocumentReference/cbc:ID") == "VALE-SALIDA-0042"
    assert f.texto(xml, "cac:AdditionalDocumentReference/cbc:DocumentTypeCode") == "99"
    assert not f.todos(xml, "cac:DespatchDocumentReference")


def test_nota_de_credito_referencia_y_motivo_catalogo_09():
    xml = f.arbol(f.nota_credito())
    assert f.texto(xml, "cac:DiscrepancyResponse/cbc:ReferenceID") == "F001-1"
    assert f.texto(xml, "cac:DiscrepancyResponse/cbc:ResponseCode") == "07"
    assert f.texto(xml, "cac:DiscrepancyResponse/cbc:ResponseCode/@listURI").endswith("catalogo09")
    assert f.texto(xml, "cac:DiscrepancyResponse/cbc:Description") == "Sustento de la nota"
    assert f.texto(xml, "cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID") == "F001-1"
    assert f.texto(xml, "cac:BillingReference/cac:InvoiceDocumentReference/cbc:DocumentTypeCode") == "01"


def test_nota_de_debito_motivo_catalogo_10():
    xml = f.arbol(f.nota_debito())
    assert f.texto(xml, "cac:DiscrepancyResponse/cbc:ResponseCode") == "01"
    assert f.texto(xml, "cac:DiscrepancyResponse/cbc:ResponseCode/@listURI").endswith("catalogo10")
