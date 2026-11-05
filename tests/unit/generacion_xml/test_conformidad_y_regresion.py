"""Taller 2 · Generación: conformidad con el XSD oficial y regresión contra XML de referencia.

Los XML de referencia viven en ``tests/unit/generacion_xml/esperados``. Si un cambio en el
generador es intencional, se regeneran con:  ``ACTUALIZAR_ESPERADOS=1 pytest tests/unit/generacion_xml``
y el diff de esos archivos queda a la vista en la revisión del cambio.
"""

import os
from pathlib import Path

import pytest

from src.adapters.outbound.firma.xmldsig import CertificadoDigital, FirmaXmlDsig
from src.adapters.outbound.ubl.validador import ValidadorXsdLxml
from tests.unit.generacion_xml import fabrica as f

ESPERADOS = Path(__file__).parent / "esperados"
VALIDADOR = ValidadorXsdLxml()
ESCENARIOS = sorted(f.ESCENARIOS)


@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_cada_escenario_valida_contra_el_xsd_oficial(escenario):
    comprobante = f.ESCENARIOS[escenario]()
    VALIDADOR.validar(f.generar(comprobante), comprobante.tipo)


@pytest.mark.parametrize("texto", ['Arroz & Azúcar', '<script>', 'Comillas "dobles" y \'simples\'', 'Ñandú ½ kg €',
                                   ']]> fin de CDATA', 'tab\tinterno'])
def test_cualquier_texto_del_usuario_produce_xml_valido(texto):
    comprobante = f.armar(f.TipoComprobante.FACTURA, "F001", (f.linea(1, texto),))
    xml = f.generar(comprobante)
    VALIDADOR.validar(xml, comprobante.tipo)
    assert f.texto(f.arbol(comprobante), "cac:InvoiceLine/cac:Item/cbc:Description") == texto


@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_regresion_contra_xml_de_referencia(escenario):
    generado = f.generar(f.ESCENARIOS[escenario]())
    archivo = ESPERADOS / f"{escenario}.xml"
    if os.environ.get("ACTUALIZAR_ESPERADOS") == "1":
        ESPERADOS.mkdir(exist_ok=True)
        archivo.write_bytes(generado)
    assert archivo.exists(), f"Falta {archivo.name}: ejecute con ACTUALIZAR_ESPERADOS=1"
    assert generado == archivo.read_bytes()


def test_la_generacion_es_determinista():
    assert f.generar(f.factura_completa()) == f.generar(f.factura_completa())


def test_el_digest_value_depende_solo_del_contenido_y_no_del_certificado():
    """El hash CPE es reproducible: dos certificados distintos producen el mismo DigestValue."""
    xml = f.generar(f.factura_completa())
    uno = FirmaXmlDsig(CertificadoDigital.autofirmado_para_desarrollo("20556677884", "A")).firmar(xml)
    dos = FirmaXmlDsig(CertificadoDigital.autofirmado_para_desarrollo("20556677884", "B")).firmar(xml)
    assert uno.digest_value == dos.digest_value
    assert uno.xml != dos.xml  # la firma (SignatureValue) sí cambia


def test_cambiar_un_dato_del_dominio_cambia_el_digest_value():
    firma = FirmaXmlDsig(CertificadoDigital.autofirmado_para_desarrollo("20556677884", "A"))
    original = firma.firmar(f.generar(f.factura_contado())).digest_value
    otro = firma.firmar(f.generar(f.armar(f.TipoComprobante.FACTURA, "F001", (f.linea(1, cantidad="51"),))))
    assert otro.digest_value != original
