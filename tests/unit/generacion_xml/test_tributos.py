"""Taller 2 · Generación: tributos por línea y del documento (Catálogos 05, 07 y 08; ICBPER)."""

from decimal import Decimal as D

import pytest

from tests.unit.generacion_xml import fabrica as f

LINEA = "cac:InvoiceLine[{n}]/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='{tributo}']"


def subtotal(n: int, tributo: str) -> str:
    return LINEA.format(n=n, tributo=tributo)


def test_igv_gravado_categoria_s_18_por_ciento_y_afectacion_10():
    xml = f.arbol(f.factura_completa())
    s = subtotal(1, "1000")
    assert f.texto(xml, f"{s}/cbc:TaxableAmount") == "210.00"
    assert f.texto(xml, f"{s}/cbc:TaxAmount") == "37.80"
    assert f.texto(xml, f"{s}/cac:TaxCategory/cbc:ID") == "S"
    assert f.texto(xml, f"{s}/cac:TaxCategory/cbc:Percent") == "18.00"
    assert f.texto(xml, f"{s}/cac:TaxCategory/cbc:TaxExemptionReasonCode") == "10"
    assert f.todos(xml, f"{s}/cac:TaxCategory/cac:TaxScheme/*") == ["1000", "IGV", "VAT"]


@pytest.mark.parametrize(("n", "tributo", "categoria", "afectacion", "nombre"), [
    (6, "9997", "E", "20", "EXO"),
    (7, "9998", "O", "30", "INA"),
])
def test_exonerado_e_inafecto(n, tributo, categoria, afectacion, nombre):
    xml = f.arbol(f.factura_completa())
    s = subtotal(n, tributo)
    assert f.texto(xml, f"{s}/cbc:TaxAmount") == "0.00"
    assert f.texto(xml, f"{s}/cac:TaxCategory/cbc:ID") == categoria
    assert f.texto(xml, f"{s}/cac:TaxCategory/cbc:TaxExemptionReasonCode") == afectacion
    assert f.texto(xml, f"{s}/cac:TaxCategory/cac:TaxScheme/cbc:Name") == nombre


def test_exportacion_9995_categoria_g():
    xml = f.arbol(f.factura_exportacion_usd())
    s = subtotal(1, "9995")
    assert (f.texto(xml, f"{s}/cac:TaxCategory/cbc:ID"),
            f.texto(xml, f"{s}/cac:TaxCategory/cbc:TaxExemptionReasonCode")) == ("G", "40")


@pytest.mark.parametrize(("n", "sistema", "monto", "base"), [
    (2, "01", "54.00", "270.00"),   # 6 x 45 x 20 %
    (3, "02", "16.20", "66.00"),    # 12 x 1.35
    (4, "03", "7.20", "42.35"),     # 4 x 12.50 x 0.847 x 17 %
])
def test_isc_catalogo_08_en_tier_range(n, sistema, monto, base):
    xml = f.arbol(f.factura_completa())
    s = subtotal(n, "2000")
    assert f.texto(xml, f"{s}/cac:TaxCategory/cbc:TierRange") == sistema
    assert f.texto(xml, f"{s}/cbc:TaxAmount") == monto
    assert f.texto(xml, f"{s}/cbc:TaxableAmount") == base
    assert f.todos(xml, f"{s}/cac:TaxCategory/cac:TaxScheme/*") == ["2000", "ISC", "EXC"]


def test_isc_al_valor_lleva_porcentaje_y_monto_fijo_lleva_importe_por_unidad():
    xml = f.arbol(f.factura_completa())
    assert f.texto(xml, f"{subtotal(2, '2000')}/cac:TaxCategory/cbc:Percent") == "20.00"
    assert f.texto(xml, f"{subtotal(3, '2000')}/cac:TaxCategory/cbc:PerUnitAmount") == "1.35"


def test_el_igv_se_calcula_sobre_valor_de_venta_mas_isc():
    xml = f.arbol(f.factura_completa())
    assert f.texto(xml, f"{subtotal(2, '1000')}/cbc:TaxableAmount") == "324.00"  # 270 + 54
    assert f.texto(xml, f"{subtotal(2, '1000')}/cbc:TaxAmount") == "58.32"


def test_icbper_por_bolsa():
    xml = f.arbol(f.factura_completa())
    s = subtotal(5, "7152")
    assert f.texto(xml, f"{s}/cbc:TaxAmount") == "1.50"
    assert f.texto(xml, f"{s}/cbc:BaseUnitMeasure") == "3"
    assert f.texto(xml, f"{s}/cac:TaxCategory/cbc:PerUnitAmount") == "0.50"
    assert f.todos(xml, f"{s}/cac:TaxCategory/cac:TaxScheme/*") == ["7152", "ICBPER", "OTH"]


def test_tax_total_de_cada_linea_suma_sus_subtotales():
    xml = f.arbol(f.factura_completa())
    for n in range(1, 8):
        total = D(f.texto(xml, f"cac:InvoiceLine[{n}]/cac:TaxTotal/cbc:TaxAmount"))
        partes = sum(D(x) for x in f.todos(xml, f"cac:InvoiceLine[{n}]/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount"))
        assert total == partes


def test_tax_total_del_documento_suma_el_de_las_lineas():
    xml = f.arbol(f.factura_completa())
    lineas = sum(D(x) for x in f.todos(xml, "cac:InvoiceLine/cac:TaxTotal/cbc:TaxAmount"))
    assert D(f.texto(xml, "cac:TaxTotal/cbc:TaxAmount")) == lineas


def test_subtotales_del_documento_por_tributo():
    xml = f.arbol(f.factura_completa())
    esquemas = f.todos(xml, "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID")
    assert esquemas == ["1000", "2000", "9997", "9998", "7152"]


# --- Reglas de validación de SUNAT detectadas por el servicio beta ----------------------
# La OSE simulada solo verifica firma y XSD. Estas dos reglas las rechazó el servicio beta
# real (docs/evidencia-sunat/) y quedan aquí como regresión para todos los comprobantes.

LINEAS = "*[self::cac:InvoiceLine or self::cac:CreditNoteLine or self::cac:DebitNoteLine]"
COMPROBANTES = [f.factura_completa, f.factura_contado, f.factura_credito, f.factura_exportacion_usd, f.boleta,
                f.nota_credito, f.nota_debito]


@pytest.mark.parametrize("fabricar", COMPROBANTES, ids=lambda c: c.__name__)
def test_regla_3108_base_por_tasa_es_el_monto_del_isc(fabricar):
    """3108: TaxableAmount x Percent / 100 = TaxAmount del ISC (±1), también en el sistema 02."""
    xml = f.arbol(fabricar())
    for isc in xml.xpath(f"{LINEAS}/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='2000']",
                         namespaces=f.NS):
        base, monto = D(f.texto(isc, "cbc:TaxableAmount")), D(f.texto(isc, "cbc:TaxAmount"))
        tasa = D(f.texto(isc, "cac:TaxCategory/cbc:Percent"))
        assert abs(base * tasa / 100 - monto) <= 1


def test_isc_monto_fijo_informa_la_tasa_equivalente():
    xml = f.arbol(f.factura_completa())
    assert f.texto(xml, f"{subtotal(3, '2000')}/cac:TaxCategory/cbc:Percent") == "24.54545"  # 16.20 / 66.00


@pytest.mark.parametrize("fabricar", COMPROBANTES, ids=lambda c: c.__name__)
def test_regla_3277_base_global_del_igv_es_el_valor_de_venta_gravado_sin_isc(fabricar):
    """3277: el TaxableAmount global del tributo 1000 suma los LineExtensionAmount con afectación 10."""
    xml = f.arbol(fabricar())
    gravadas = sum((D(x) for x in f.todos(
        xml, f"{LINEAS}[cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReasonCode='10']"
             "/cbc:LineExtensionAmount")), D("0.00"))
    base_global = f.todos(xml, "cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='1000']"
                               "/cbc:TaxableAmount")
    assert [D(b) for b in base_global] == ([gravadas] if gravadas else [])
