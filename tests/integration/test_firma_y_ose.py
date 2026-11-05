"""Integración de adaptadores: generador UBL + firma XMLDSig + validador XSD + OSE simulada.

Las pruebas unitarias de la GENERACIÓN del XML (Taller 2) están en ``tests/unit/generacion_xml``.
"""

import datetime as dt

import pytest
from lxml import etree
from signxml import XMLVerifier

from src.adapters.outbound.firma.xmldsig import CertificadoDigital, FirmaXmlDsig
from src.adapters.outbound.ose.simulada import OseSimulada
from src.adapters.outbound.reloj import RelojFijo
from src.adapters.outbound.ubl import ID_FIRMA
from src.adapters.outbound.ubl.validador import ValidadorXsdLxml, parser_seguro
from src.application.errores import XmlNoConformeXsd
from src.domain.catalogos import TipoComprobante
from tests.unit.generacion_xml import fabrica as f

CERTIFICADO = CertificadoDigital.autofirmado_para_desarrollo("20556677884", "ABC SOFTWARE CORP S.A.C.")
VALIDADOR = ValidadorXsdLxml()


def firmar(comprobante):
    return FirmaXmlDsig(CERTIFICADO).firmar(f.generar(comprobante))


@pytest.mark.parametrize("escenario", sorted(f.ESCENARIOS))
def test_valida_contra_el_xsd_oficial_completo_despues_de_firmar(escenario):
    comprobante = f.ESCENARIOS[escenario]()
    VALIDADOR.validar(firmar(comprobante).xml, comprobante.tipo)


def test_el_validador_rechaza_xml_que_no_cumple_el_xsd():
    with pytest.raises(XmlNoConformeXsd):
        VALIDADOR.validar(b"<Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'/>",
                          TipoComprobante.FACTURA)


def test_el_parser_no_resuelve_entidades_externas_xxe(tmp_path):
    secreto = tmp_path / "secreto.txt"
    secreto.write_text("CLAVE-PRIVADA-123", encoding="utf-8")
    malicioso = (f'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "{secreto.as_uri()}">]>'
                 f"<x>&e;</x>").encode()
    assert b"CLAVE-PRIVADA-123" not in etree.tostring(etree.fromstring(malicioso, parser_seguro()))
    # Control: un parser permisivo SÍ filtraría el archivo; por eso el adaptador usa parser_seguro().
    permisivo = etree.XMLParser(resolve_entities=True, load_dtd=True, no_network=True)
    assert b"CLAVE-PRIVADA-123" in etree.tostring(etree.fromstring(malicioso, permisivo))


def test_firma_xmldsig_en_ubl_extensions_y_hash_cpe_es_el_digest_value():
    firmado = firmar(f.factura_completa())
    raiz = etree.fromstring(firmado.xml)
    assert etree.QName(raiz[0]).localname == "UBLExtensions"
    firma = raiz.find("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/ds:Signature", f.NS)
    assert firma is not None and firma.get("Id") == ID_FIRMA
    assert firmado.digest_value == raiz.find(".//ds:DigestValue", f.NS).text
    XMLVerifier().verify(raiz, x509_cert=CERTIFICADO.certificado_pem.decode(), expect_references=1)


def test_la_ose_simulada_acepta_y_detecta_un_xml_alterado_despues_de_firmar():
    firmado = firmar(f.factura_contado())
    ose = OseSimulada(validador=VALIDADOR, reloj=RelojFijo(dt.datetime(2026, 10, 22, 11)))
    assert ose.enviar("20556677884-01-F001-1", firmado.xml).codigo == "0"
    alterado = firmado.xml.replace(b"EL SOL &amp; CIA", b"OTRO CLIENTE")
    assert alterado != firmado.xml
    assert ose.enviar("20556677884-01-F001-1", alterado).codigo == "2335"
