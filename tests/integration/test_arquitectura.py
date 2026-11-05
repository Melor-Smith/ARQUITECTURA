"""Pruebas de arquitectura: la regla de dependencias del hexágono se verifica, no solo se dibuja.

    adapters  ->  application  ->  domain
    (FastAPI,       (casos de uso,    (entidades, objetos de valor,
     xsdata,         puertos)          reglas SUNAT; solo stdlib)
     lxml, signxml)
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"


def importaciones(paquete: str) -> list[tuple[str, str]]:
    resultado = []
    for archivo in (SRC / paquete).rglob("*.py"):
        if "generated" in archivo.parts:
            continue
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                resultado.append((archivo.relative_to(SRC).as_posix(), nodo.module))
            elif isinstance(nodo, ast.Import):
                resultado.extend((archivo.relative_to(SRC).as_posix(), a.name) for a in nodo.names)
    return resultado


PERMITIDO = {
    "domain": ("src.domain",),
    "application": ("src.domain", "src.application"),
}
TERCEROS_PROHIBIDOS = ("fastapi", "pydantic", "starlette", "lxml", "xsdata", "signxml", "cryptography", "uvicorn")


@pytest.mark.parametrize("capa", ["domain", "application"])
def test_el_nucleo_no_depende_de_frameworks_ni_de_adaptadores(capa):
    violaciones = [
        (archivo, modulo) for archivo, modulo in importaciones(capa)
        if modulo.split(".")[0] in TERCEROS_PROHIBIDOS
        or (modulo.startswith("src.") and not modulo.startswith(PERMITIDO[capa]))
    ]
    assert violaciones == []


def test_ningun_modulo_de_produccion_importa_desde_tests():
    violaciones = [(a, m) for a, m in importaciones("") if m == "tests" or m.startswith("tests.")]
    assert violaciones == []


def test_los_puertos_son_interfaces():
    from typing import Protocol

    from src.application import puertos

    for nombre in ("RepositorioComprobantes", "SecuenciaCorrelativos", "GeneradorUBL", "ValidadorEsquemaUBL",
                   "FirmaDigital", "ClienteOSE", "RepositorioKardex"):
        assert Protocol in getattr(puertos, nombre).__mro__, nombre


def test_los_casos_de_uso_reciben_sus_dependencias_por_constructor():
    import inspect

    from src.application.casos_uso.comprobantes import EmitirComprobante

    parametros = inspect.signature(EmitirComprobante).parameters
    assert {"comprobantes", "secuencia", "generador_ubl", "firma", "ose"} <= set(parametros)
