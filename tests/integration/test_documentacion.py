"""La documentación no puede afirmar cifras que el repositorio no respalda.

Los artefactos generados (OpenAPI, matriz, paquete PLE) ya tienen su prueba. Esta cubre lo
escrito a mano: cada número que la documentación declara se compara con su fuente real.
Si se agrega una prueba, un ADR o una fila de la matriz y no se actualiza la documentación,
la CI falla y dice qué archivo corregir.
"""

from __future__ import annotations

import re
import subprocess
import sys
from functools import cache
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
DOCUMENTOS = [RAIZ / "README.md", *sorted((RAIZ / "docs").rglob("*.md")), *sorted((RAIZ / "specs").rglob("*.md"))]


@cache
def _recolectadas(ruta: str = "tests") -> int:
    salida = subprocess.run([sys.executable, "-m", "pytest", "--co", "-q", "-p", "no:cacheprovider", ruta],
                            cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    return int(re.search(r"(\d+) tests? collected", salida).group(1))


def _menciones(patron: str) -> list[tuple[str, int]]:
    """(archivo, número) por cada vez que la documentación declara una cifra con ese patrón."""
    return [(str(doc.relative_to(RAIZ)), int(m.group(1)))
            for doc in DOCUMENTOS for m in re.finditer(patron, doc.read_text(encoding="utf-8"))]


def _comprobar(patron: str, real: int) -> None:
    menciones = _menciones(patron)
    assert menciones, f"ninguna mención encontrada para {patron!r}"
    assert [m for m in menciones if m[1] != real] == [], f"la cifra real es {real}"


def test_cantidad_total_de_pruebas():
    total = _recolectadas()
    patrones = (
        r"\*\*(\d+)\*\*, en Python",
        r"\((\d+) pruebas\)(?!\. Detalle)",  # "(77 pruebas). Detalle" es el Taller 2, no el total
        r"# (\d+) pruebas\b(?! unitarias)",
        r"de 20 a (\d+) pruebas",
    )
    for patron in patrones:
        _comprobar(patron, total)


def test_cantidad_de_pruebas_de_generacion_del_taller_2():
    real = _recolectadas("tests/unit/generacion_xml")
    for patron in (r"(\d+) pruebas unitarias de generación", r"# (\d+) pruebas unitarias",
                   r"\((\d+) pruebas\)\. Detalle", r"(\d+) pruebas de generación"):
        if _menciones(patron):
            _comprobar(patron, real)


def test_archivos_revisados_por_mypy():
    propios = [p for p in (RAIZ / "src").rglob("*.py") if "generated" not in p.parts]
    _comprobar(r"\*\*0 errores\*\* en (\d+) archivos", len(propios) + len(list((RAIZ / "scripts").glob("*.py"))))


def test_filas_y_xpath_de_la_matriz():
    datos = yaml.safe_load((RAIZ / "specs/traceability/matriz.yaml").read_text(encoding="utf-8"))
    filas = [f for seccion in datos["secciones"] for f in seccion["filas"]]
    _comprobar(r"(\d+) filas", len(filas))
    _comprobar(r"(\d+) XPath", sum(1 for f in filas if f.get("xpath")))


def test_contraejemplos():
    _comprobar(r"(\d+) contraejemplos", len(list((RAIZ / "specs/ejemplos/invalidos").glob("*.json"))))


def test_rango_de_adr():
    ultimo = max(int(p.name[:4]) for p in (RAIZ / "specs/adr").glob("[0-9][0-9][0-9][0-9]-*.md"))
    _comprobar(r"0001 a (\d{4})", ultimo)
    _comprobar(r"\(0001-(\d{4})\)", ultimo)  # p. ej. "(0001-0011)"; no confundir con "0001-4587"


@pytest.mark.parametrize("afirmacion", [
    r"12\.1[^.\n]{0,40}usan? la tabla 6",  # el PLE 5.2.0.7 exige UN/ECE en el campo 16
    r"persistencia es (solo )?en memoria\.",  # hay adaptador SQLite (ADR 0011)
    r"OSE es (un adaptador )?\*\*simulad",  # hay envío real a SUNAT, probado en beta (ADR 0012)
])
def test_no_quedan_afirmaciones_superadas(afirmacion):
    hallazgos = [str(d.relative_to(RAIZ)) for d in DOCUMENTOS if re.search(afirmacion, d.read_text(encoding="utf-8"))]
    assert hallazgos == []
