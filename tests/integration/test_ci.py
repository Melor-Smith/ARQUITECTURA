"""Cadena de suministro de la CI: cada GitHub Action se fija por SHA de commit, no por etiqueta.

Una etiqueta (``@v4``) se puede mover a otro commit; un SHA no. El comentario al final de la
línea (``# v4.4.0``) dice a qué versión corresponde, para que una persona pueda revisarlo.
"""

from __future__ import annotations

import re

from tests.conftest import RAIZ

WORKFLOWS = sorted((RAIZ / ".github" / "workflows").glob("*.yml"))
USES = re.compile(r"uses:\s*(\S+)(.*)")


def test_cada_action_esta_fijada_por_sha_con_su_version_comentada():
    usos = [(w.name, m.group(1), m.group(2)) for w in WORKFLOWS for m in USES.finditer(w.read_text(encoding="utf-8"))]
    assert usos
    sin_fijar = [(w, accion) for w, accion, comentario in usos
                 if not re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", accion) or not re.search(r"#\s*v\d", comentario)]
    assert sin_fijar == []
