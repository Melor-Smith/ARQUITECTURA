"""Lanzador ``iniciar.py``: arranca el formulario con un solo comando, solo con la biblioteca estándar."""

from __future__ import annotations

import ast
import socket
import sys
from pathlib import Path

import iniciar

RAIZ = Path(__file__).resolve().parents[2]


def test_exige_python_3_10_o_superior():
    assert iniciar.version_soportada((3, 10))
    assert iniciar.version_soportada((3, 13))
    assert not iniciar.version_soportada((3, 9))


def test_solo_usa_la_biblioteca_estandar_porque_corre_antes_de_instalar_nada():
    arbol = ast.parse((RAIZ / "iniciar.py").read_text(encoding="utf-8"))
    modulos = {a.name.split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.Import) for a in n.names}
    modulos |= {n.module.split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom) and n.module}
    assert modulos - {"__future__"} <= set(sys.stdlib_module_names)


def test_instala_la_primera_vez_y_cuando_cambian_los_requisitos(tmp_path):
    requisitos, marca = tmp_path / "requirements.txt", tmp_path / "marca"
    requisitos.write_text("fastapi==1\n", encoding="utf-8")
    assert iniciar.necesita_instalar(marca, requisitos)
    marca.write_text(iniciar.huella_requisitos(requisitos), encoding="utf-8")
    assert not iniciar.necesita_instalar(marca, requisitos)
    requisitos.write_text("fastapi==2\n", encoding="utf-8")
    assert iniciar.necesita_instalar(marca, requisitos)


def test_si_el_puerto_esta_ocupado_usa_el_siguiente():
    with socket.socket() as ocupado:
        ocupado.bind(("127.0.0.1", 0))
        ocupado.listen()
        puerto = ocupado.getsockname()[1]
        assert iniciar.puerto_libre(puerto) != puerto


def test_el_bat_llama_al_lanzador_desde_su_propia_carpeta():
    bat = (RAIZ / "iniciar.bat").read_text(encoding="utf-8")
    assert 'cd /d "%~dp0"' in bat and "iniciar.py" in bat
