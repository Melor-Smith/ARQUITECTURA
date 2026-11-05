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


# --- Ubicaciones fuera del XML: campos del PLE y contrato OpenAPI ---------------------
# No todo dato tiene XPath (inventario, tipo de cambio). Esas filas se anclan al campo del
# TXT del PLE o al contrato de la API, y esas columnas también se verifican: ninguna fila
# queda sin al menos una ubicación comprobada contra un artefacto real.

COLUMNAS_FUENTE = {"id", "dato", "norma", "sunat", "xpath", "contrato", "legado", "ple_141", "ple_121", "error",
                   "prueba"}
PAQUETE_PLE = RAIZ / "docs" / "evidencia-ple" / "paquete"
OPENAPI = yaml.safe_load((RAIZ / "specs" / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))


def test_cada_fila_usa_solo_columnas_conocidas():
    # Una coma sin comillas en un mapeo YAML en línea crea columnas falsas y trunca el valor
    # (le pasó a T42: "UN/ECE 5305 (S, E, O, G)" se partió en cuatro claves).
    raras = {fila["id"]: sorted(set(fila) - COLUMNAS_FUENTE) for fila in FILAS if set(fila) - COLUMNAS_FUENTE}
    assert raras == {}


def _campos_ple(valor: object) -> list[int]:
    """'17 / 18 (salida en negativo)' -> [17, 18]; '(nombre de archivo)' -> []."""
    inicio = re.match(r"[\d,/\s]+", str(valor or ""))
    return [int(n) for n in re.findall(r"\d+", inicio.group(0))] if inicio else []


def _columnas_txt(libro: str) -> list[list[str]]:
    lineas = []
    for archivo in PAQUETE_PLE.rglob(f"LE*{libro}00*.TXT"):
        # read_bytes: read_text convertiría el CRLF del formato en "\n".
        lineas += [ln.split("|")[:-1] for ln in archivo.read_bytes().decode("utf-8").split("\r\n") if ln]
    return lineas


@pytest.mark.parametrize(("columna", "libro", "estructura"), [
    ("ple_141", "1401", "ESTRUCTURA_141"),
    ("ple_121", "1201", "ESTRUCTURA_121"),
])
def test_cada_campo_ple_citado_existe_en_el_anexo_2_y_el_sistema_lo_llena(columna, libro, estructura):
    from src.domain import ple_estructura

    campos = {c.numero for c in getattr(ple_estructura, estructura)}
    lineas = _columnas_txt(libro)
    assert lineas, f"no hay TXT {libro} en {PAQUETE_PLE}"
    citados = {(fila["id"], n) for fila in FILAS for n in _campos_ple(fila.get(columna))}
    assert citados
    assert {(i, n) for i, n in citados if n not in campos} == set(), "campo inexistente en el Anexo 2"
    vacios = {(i, n) for i, n in citados if not any(ln[n - 1] for ln in lineas)} - set(SIN_MUESTRA_EN_EL_PAQUETE)
    assert vacios == set(), "el TXT generado nunca llena ese campo"


#: Campos condicionales que los ejemplos del caso no llenan, con la prueba que sí los ejerce.
SIN_MUESTRA_EN_EL_PAQUETE = {
    ("T66", 5): "test_credito_que_vence_el_mes_siguiente_informa_el_campo_5",  # el crédito del caso vence en 2027
}


def test_los_campos_sin_muestra_tienen_su_prueba():
    definidas = "\n".join(p.read_text(encoding="utf-8") for p in (RAIZ / "tests").rglob("test_*.py"))
    assert all(f"def {prueba}(" in definidas for prueba in SIN_MUESTRA_EN_EL_PAQUETE.values())


def _resolver(esquema: dict, ruta: list[str]) -> bool:
    if "$ref" in esquema:
        return _resolver(OPENAPI["components"]["schemas"][esquema["$ref"].rsplit("/", 1)[1]], ruta)
    for clave in ("anyOf", "oneOf", "allOf"):
        if clave in esquema:
            return any(_resolver(rama, ruta) for rama in esquema[clave])
    if "items" in esquema:
        return _resolver(esquema["items"], ruta)
    if not ruta:
        return True
    return ruta[0] in esquema.get("properties", {}) and _resolver(esquema["properties"][ruta[0]], ruta[1:])


def _ruta_contrato(valor: object) -> list[str]:
    """'lineas[].isc.monto (respuesta)' -> ['lineas', 'isc', 'monto']; '(constante)' -> []."""
    texto = re.sub(r"\s*\(.*\)$", "", str(valor or "")).replace("[]", "")
    return texto.split(".") if texto else []


CON_CONTRATO = [fila for fila in FILAS if _ruta_contrato(fila.get("contrato"))]


@pytest.mark.parametrize("fila", CON_CONTRATO, ids=[x["id"] for x in CON_CONTRATO])
def test_cada_campo_del_contrato_existe_en_el_openapi(fila):
    ruta = _ruta_contrato(fila["contrato"])
    assert any(_resolver(esquema, ruta) for esquema in OPENAPI["components"]["schemas"].values()), fila["contrato"]


def test_ninguna_fila_queda_sin_ubicacion_verificada():
    sin_ubicacion = [fila["id"] for fila in FILAS
                     if not (fila.get("xpath") or _campos_ple(fila.get("ple_141")) or _campos_ple(fila.get("ple_121"))
                             or _ruta_contrato(fila.get("contrato")))]
    assert sin_ubicacion == []
