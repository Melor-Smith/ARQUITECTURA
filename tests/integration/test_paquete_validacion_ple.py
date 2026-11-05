"""El paquete de validación PLE del repositorio es reproducible y sigue siendo el que validó SUNAT.

* ``docs/evidencia-ple/paquete/`` es exactamente lo que genera ``scripts/preparar_validacion_ple.py``.
* El 12.1 tiene la huella SHA-256 del archivo que el programa PLE 5.2.0.7 de SUNAT validó "sin
  inconsistencias" el 05/11/2026 (constancia en ``docs/evidencia-ple/``). Si un cambio en el
  código altera ese TXT, esta prueba falla: hay que volver a validarlo con el PLE y actualizar
  la huella y la constancia, no solo la prueba.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.preparar_validacion_ple import DESTINO, paquete
from src.domain.ple_estructura import ESTRUCTURA_121, ESTRUCTURA_141, validar_linea

#: SHA-256 del 12.1 validado por SUNAT (constancia-sunat-12.1-sin-errores.pdf).
HUELLA_VALIDADA_POR_SUNAT = "589d39b5490cecb15c88c77f1a19b62fa4235bdc9f004cf579355f5e1c3edb6b"


@pytest.fixture(scope="module")
def generado() -> dict[str, bytes]:
    return paquete()


def test_el_paquete_versionado_es_el_que_genera_el_sistema(generado):
    versionado = {str(p.relative_to(DESTINO)).replace("\\", "/"): p.read_bytes()
                  for p in DESTINO.rglob("*") if p.is_file()}
    assert sorted(versionado) == sorted(generado), "ejecute: python scripts/preparar_validacion_ple.py"
    desactualizados = [r for r in generado if generado[r] != versionado[r]]
    assert desactualizados == [], "ejecute: python scripts/preparar_validacion_ple.py"


def test_el_12_1_es_el_mismo_que_valido_sunat(generado):
    [(nombre, contenido)] = [(r, c) for r, c in generado.items() if r.startswith("12.1-")]
    assert hashlib.sha256(contenido).hexdigest() == HUELLA_VALIDADA_POR_SUNAT, (
        f"{nombre} cambió respecto del archivo que SUNAT validó: vuelva a validarlo con el PLE "
        "y actualice la constancia y la huella")
    assert Path("docs/evidencia-ple/constancia-sunat-12.1-sin-errores.pdf").exists()


@pytest.mark.parametrize("prefijo", ["12.1-", "14.1-octubre", "14.1-marzo"])
def test_cada_txt_del_sistema_cumple_el_anexo_2(generado, prefijo):
    estructura = ESTRUCTURA_121 if prefijo.startswith("12.1") else ESTRUCTURA_141
    libro = "120100" if prefijo.startswith("12.1") else "140100"
    [contenido] = [c for r, c in generado.items() if r.startswith(prefijo) and libro in r]
    lineas = contenido.decode("utf-8").split("\r\n")[:-1]
    assert lineas
    assert [e for n, ln in enumerate(lineas, 1) for e in validar_linea(estructura, ln, n)] == []


def test_ventas_y_compras_van_juntas_como_exige_el_ple(generado):
    for carpeta in ("14.1-octubre-2026", "14.1-marzo-2022"):
        libros = sorted(r.split("/")[1][21:27] for r in generado if r.startswith(carpeta))
        assert libros == ["080100", "080200", "140100"]


def test_la_compra_de_prueba_tiene_los_42_campos_del_8_1(generado):
    [compra] = [c for r, c in generado.items() if r.startswith("14.1-marzo") and "080100" in r]
    linea = compra.decode("utf-8").removesuffix("\r\n")
    assert linea.endswith("|") and len(linea[:-1].split("|")) == 42
