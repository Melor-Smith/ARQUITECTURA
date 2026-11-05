"""Cada diagrama tiene su fuente (.mmd) y su versión renderizada (.svg y .png), y la documentación lo enlaza.

Renderizar: ``scripts/renderizar_diagramas.ps1`` (Windows) o ``sh scripts/renderizar_diagramas.sh``.
La CI renderiza además cada .mmd desde cero (job ``diagramas``), así que una fuente con
error de sintaxis también la hace fallar.
"""

from __future__ import annotations

import re

import pytest

from tests.conftest import RAIZ

DIAGRAMAS = RAIZ / "docs" / "diagramas"
FUENTES = sorted(DIAGRAMAS.glob("*.mmd"))

#: Lo que pidió la revisión: contexto y contenedores C4, MVC, hexagonal, evolución, clases del
#: dominio, secuencia de emisión, estados del comprobante y despliegue.
ESPERADOS = {"01-contexto-c4", "02-contenedores-c4", "03-mvc-actual", "04-hexagonal", "05-evolucion",
             "06-clases-dominio", "07-secuencia-emision", "08-estados-comprobante", "09-despliegue"}


def test_estan_los_nueve_diagramas():
    assert {p.stem for p in FUENTES} == ESPERADOS


@pytest.mark.parametrize("fuente", FUENTES, ids=lambda p: p.stem)
@pytest.mark.parametrize("formato", ["svg", "png"])
def test_cada_fuente_tiene_su_render(fuente, formato):
    render = fuente.with_suffix(f".{formato}")
    assert render.exists(), f"falta {render.name}: ejecute scripts/renderizar_diagramas.ps1"
    assert render.stat().st_size > 1000, f"{render.name} está vacío o incompleto"


@pytest.mark.parametrize("fuente", FUENTES, ids=lambda p: p.stem)
def test_cada_svg_es_un_svg_de_mermaid(fuente):
    svg = fuente.with_suffix(".svg")
    if not svg.exists():
        pytest.fail(f"falta {svg.name}")
    texto = svg.read_text(encoding="utf-8", errors="replace")
    assert "<svg" in texto
    assert "Syntax error" not in texto, f"{fuente.name} tiene un error de sintaxis Mermaid"


def test_cada_diagrama_esta_enlazado_desde_la_documentacion():
    documentos = [RAIZ / "README.md", *(RAIZ / "specs").rglob("*.md"), *(RAIZ / "docs").rglob("*.md")]
    texto = "\n".join(d.read_text(encoding="utf-8") for d in documentos)
    sin_enlace = [f.stem for f in FUENTES if not re.search(re.escape(f.stem) + r"\.(svg|png|mmd)", texto)]
    assert sin_enlace == []
