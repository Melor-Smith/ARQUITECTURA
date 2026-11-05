"""La matriz de trazabilidad se verifica contra el código, los XSD y XML reales generados."""

import re
from collections import defaultdict

import pytest
import yaml
from lxml import etree

from scripts import matriz
from src.adapters.outbound.firma.xmldsig import CertificadoDigital, FirmaXmlDsig
from tests.conftest import RAIZ
from tests.unit.generacion_xml import fabrica as f

FILAS = [fila for s in yaml.safe_load(matriz.FUENTE.read_text(encoding="utf-8"))["secciones"] for fila in s["filas"]]
CON_XPATH = [fila for fila in FILAS if fila.get("xpath")]


@pytest.fixture(scope="module")
def xml_por_raiz() -> dict[str, list[etree._Element]]:
    firma = FirmaXmlDsig(CertificadoDigital.autofirmado_para_desarrollo("20556677884", "PRUEBA"))
    documentos = defaultdict(list)
    for escenario in f.ESCENARIOS.values():
        raiz = etree.fromstring(firma.firmar(f.generar(escenario())).xml)
        documentos[etree.QName(raiz).localname].append(raiz)
    return documentos


def evaluar(xpath: str, raiz: etree._Element) -> list:
    nombre = xpath.split("/")[1]
    absoluto = xpath.replace(f"/{nombre}", "/doc:" + nombre, 1)
    return raiz.xpath(absoluto, namespaces={**f.NS, "doc": matriz.RAICES[nombre]})


@pytest.mark.parametrize("fila", CON_XPATH, ids=[x["id"] for x in CON_XPATH])
def test_cada_xpath_de_la_matriz_existe_en_un_xml_generado(fila, xml_por_raiz):
    raiz = fila["xpath"].split("/")[1]
    assert any(evaluar(fila["xpath"], documento) for documento in xml_por_raiz[raiz]), fila["xpath"]


def test_cada_prueba_citada_existe():
    definidas = set()
    for archivo in (RAIZ / "tests").rglob("test_*.py"):
        definidas |= set(re.findall(r"def (test_\w+)", archivo.read_text(encoding="utf-8")))
    faltantes = {fila["prueba"] for fila in FILAS if fila.get("prueba")} - definidas
    assert faltantes == set()


def test_cada_codigo_de_error_citado_existe_en_el_codigo():
    fuentes = [p for p in (RAIZ / "src").rglob("*.py") if "generated" not in p.parts]
    codigo = "\n".join(p.read_text(encoding="utf-8") for p in fuentes)
    faltantes = {fila["error"] for fila in FILAS if fila.get("error") and fila["error"] not in codigo}
    assert faltantes == set()


def test_identificadores_unicos():
    ids = [fila["id"] for fila in FILAS]
    assert len(ids) == len(set(ids))


def test_la_matriz_generada_esta_al_dia():
    datos = matriz.filas()
    assert matriz.DESTINO_MD.read_text(encoding="utf-8") == matriz.documento_markdown(datos), \
        "Ejecute: python scripts/matriz.py"
    assert matriz.DESTINO_CSV.read_text(encoding="utf-8-sig") == matriz.csv_texto(datos)


@pytest.mark.parametrize(("xpath", "esperado", "obligatorio"), [
    ("/Invoice/cbc:ID", "1..1", True),
    ("/Invoice/cbc:InvoiceTypeCode", "0..1", False),  # SUNAT lo exige: brecha de perfil
    ("/Invoice/cac:InvoiceLine/cbc:ID", "1..1", True),
    ("/Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount/@currencyID", "atributo obligatorio", True),
    ("/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity/@unitCode", "atributo opcional", False),
    ("/DebitNote/cac:RequestedMonetaryTotal/cbc:PayableAmount", "1..1", True),
])
def test_cardinalidad_calculada_desde_el_xsd(xpath, esperado, obligatorio):
    calculada = matriz.EsquemaUBL().cardinalidad(xpath)
    assert (calculada.texto, calculada.obligatorio_en_xsd) == (esperado, obligatorio)


def test_un_xpath_inexistente_en_el_xsd_se_detecta():
    with pytest.raises(ValueError, match="no es hijo"):
        matriz.EsquemaUBL().cardinalidad("/Invoice/cbc:CampoInventado")
