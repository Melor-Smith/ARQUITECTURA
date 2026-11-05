"""Taller 2 · Generación: emisor (configuración) y adquiriente (Catálogo 06)."""

from tests.unit.generacion_xml import fabrica as f

EMISOR = "cac:AccountingSupplierParty/cac:Party"
CLIENTE = "cac:AccountingCustomerParty/cac:Party"


def test_emisor_ruc_razon_social_y_establecimiento():
    xml = f.arbol(f.factura_contado())
    assert f.texto(xml, f"{EMISOR}/cac:PartyIdentification/cbc:ID") == "20556677884"
    assert f.texto(xml, f"{EMISOR}/cac:PartyIdentification/cbc:ID/@schemeID") == "6"
    assert f.texto(xml, f"{EMISOR}/cac:PartyName/cbc:Name") == "ABC DISTRIBUCIONES"
    assert f.texto(xml, f"{EMISOR}/cac:PartyLegalEntity/cbc:RegistrationName") == "ABC SOFTWARE CORP S.A.C."
    direccion = f"{EMISOR}/cac:PartyLegalEntity/cac:RegistrationAddress"
    assert f.texto(xml, f"{direccion}/cbc:AddressTypeCode") == "0000"
    assert f.texto(xml, f"{direccion}/cbc:ID") == "150101"
    assert f.texto(xml, f"{direccion}/cac:Country/cbc:IdentificationCode") == "PE"


def test_cliente_con_ruc():
    xml = f.arbol(f.factura_contado())
    assert f.texto(xml, f"{CLIENTE}/cac:PartyIdentification/cbc:ID") == "20123456786"
    assert f.texto(xml, f"{CLIENTE}/cac:PartyIdentification/cbc:ID/@schemeID") == "6"
    assert f.texto(xml, f"{CLIENTE}/cac:PartyIdentification/cbc:ID/@schemeURI").endswith("catalogo06")


def test_cliente_con_dni_en_boleta():
    xml = f.arbol(f.boleta())
    assert f.texto(xml, f"{CLIENTE}/cac:PartyIdentification/cbc:ID/@schemeID") == "1"
    assert f.texto(xml, f"{CLIENTE}/cac:PartyLegalEntity/cbc:RegistrationName") == "MARÍA QUISPE HUAMÁN"


def test_cliente_no_domiciliado_en_exportacion():
    xml = f.arbol(f.factura_exportacion_usd())
    assert f.texto(xml, f"{CLIENTE}/cac:PartyIdentification/cbc:ID/@schemeID") == "0"


def test_nombre_con_ampersand_se_escapa_y_se_recupera_intacto():
    crudo = f.generar(f.factura_contado())
    assert b"EL SOL &amp; CIA" in crudo
    assert f.texto(f.arbol(f.factura_contado()), f"{CLIENTE}/cac:PartyLegalEntity/cbc:RegistrationName") == \
        "DISTRIBUIDORA EL SOL & CIA S.A.C."


def test_direccion_del_cliente_solo_si_existe():
    assert f.texto(f.arbol(f.factura_contado()),
                   f"{CLIENTE}/cac:PartyLegalEntity/cac:RegistrationAddress/cac:AddressLine/cbc:Line") == \
        "JR. COMERCIO 123, LIMA"
    assert not f.todos(f.arbol(f.boleta()), f"{CLIENTE}/cac:PartyLegalEntity/cac:RegistrationAddress")
