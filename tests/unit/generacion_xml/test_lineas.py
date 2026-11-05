"""Taller 2 · Generación: líneas de detalle (cantidad, unidad UNECE, precios, ítem, orden del XSD)."""

from lxml import etree

from tests.unit.generacion_xml import fabrica as f


def test_una_invoice_line_por_cada_linea_del_dominio_numerada_desde_1():
    xml = f.arbol(f.factura_completa())
    assert f.todos(xml, "cac:InvoiceLine/cbc:ID") == [str(n) for n in range(1, 8)]


def test_unidad_de_medida_catalogo_03_por_linea():
    xml = f.arbol(f.factura_completa())
    assert f.todos(xml, "cac:InvoiceLine/cbc:InvoicedQuantity/@unitCode") == \
        ["KGM", "NIU", "NIU", "NIU", "NIU", "NIU", "ZZ"]
    assert set(f.todos(xml, "cac:InvoiceLine/cbc:InvoicedQuantity/@unitCodeListID")) == {"UN/ECE rec 20"}


def test_cantidad_valor_de_venta_y_valor_unitario():
    xml = f.arbol(f.factura_contado())
    assert f.texto(xml, "cac:InvoiceLine/cbc:InvoicedQuantity") == "50"
    assert f.texto(xml, "cac:InvoiceLine/cbc:LineExtensionAmount") == "210.00"
    assert f.texto(xml, "cac:InvoiceLine/cac:Price/cbc:PriceAmount") == "4.20"


def test_precio_unitario_con_impuestos_catalogo_16():
    xml = f.arbol(f.factura_contado())
    precio = "cac:InvoiceLine/cac:PricingReference/cac:AlternativeConditionPrice"
    assert f.texto(xml, f"{precio}/cbc:PriceAmount") == "4.96"  # (210 + 37.80) / 50
    assert f.texto(xml, f"{precio}/cbc:PriceTypeCode") == "01"


def test_descripcion_y_codigo_del_producto():
    xml = f.arbol(f.factura_completa())
    assert f.texto(xml, "cac:InvoiceLine[1]/cac:Item/cbc:Description") == "Arroz extra a granel"
    assert f.texto(xml, "cac:InvoiceLine[1]/cac:Item/cac:SellersItemIdentification/cbc:ID") == "AB-ARR-001"


def test_linea_sin_producto_no_genera_sellers_item_identification():
    xml = f.arbol(f.factura_completa())
    assert not f.todos(xml, "cac:InvoiceLine[6]/cac:Item/cac:SellersItemIdentification")


def test_orden_de_elementos_de_la_linea_segun_el_xsd():
    linea = f.arbol(f.factura_completa()).find("cac:InvoiceLine", f.NS)
    orden = [etree.QName(hijo).localname for hijo in linea]
    assert orden == ["ID", "InvoicedQuantity", "LineExtensionAmount", "PricingReference", "TaxTotal", "Item",
                     "Price"]


def test_notas_usan_credited_quantity_y_debited_quantity():
    assert f.texto(f.arbol(f.nota_credito()), "cac:CreditNoteLine/cbc:CreditedQuantity") == "10"
    assert f.texto(f.arbol(f.nota_debito()), "cac:DebitNoteLine/cbc:DebitedQuantity/@unitCode") == "ZZ"
