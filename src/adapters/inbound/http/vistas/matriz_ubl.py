"""Panel "matriz" del formulario de venta: qué dato SUNAT quedó en qué etiqueta UBL 2.1.

No hay una plantilla XML con huecos. La correspondencia "dato SUNAT → XPath UBL" ya existe en la
matriz de trazabilidad del proyecto (``specs/traceability/matriz.csv``, generada desde
``matriz.yaml``). Este módulo evalúa cada XPath de esa matriz **sobre el XML recién generado** y
devuelve las filas que aplican a la venta, con el valor que quedó en el documento.

Así, el panel no repite la matriz a mano: si la matriz o el generador cambian, el panel cambia con
ellos. Si el CSV no está disponible (por ejemplo, en un empaquetado sin ``specs/``), el panel queda
vacío y el formulario sigue funcionando.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from lxml import etree

from src.adapters.outbound.ubl import NAMESPACES
from src.adapters.outbound.ubl.validador import parser_seguro

RUTA_MATRIZ = Path(__file__).resolve().parents[5] / "specs" / "traceability" / "matriz.csv"
_PREFIJOS = {k: v for k, v in NAMESPACES.items() if k in ("cac", "cbc", "ext", "ds")}
_MAXIMO_VALORES = 3


@dataclass(frozen=True, slots=True)
class FilaMatriz:
    id: str
    dato: str
    norma: str
    obligatorio: bool
    xpath: str
    valor: str


@cache
def _filas_de_la_matriz(ruta: Path = RUTA_MATRIZ) -> tuple[dict[str, str], ...]:
    try:
        with ruta.open(encoding="utf-8-sig", newline="") as archivo:
            return tuple(csv.DictReader(archivo))
    except OSError:
        return ()


def _texto(nodo: object) -> str:
    if isinstance(nodo, etree._Element):
        texto = (nodo.text or "").strip()
        return texto or f"‹{etree.QName(nodo).localname}›"  # elemento contenedor, p. ej. ds:Signature
    return str(nodo).strip()


def filas_aplicadas(xml: bytes, ruta: Path = RUTA_MATRIZ) -> list[FilaMatriz]:
    """Filas de la matriz cuyo XPath encuentra un valor en ``xml``, en el orden de la matriz."""
    raiz = etree.fromstring(xml, parser_seguro())
    nombre = etree.QName(raiz).localname
    espacios = {**_PREFIJOS, "doc": NAMESPACES[nombre]}
    resultado = []
    for fila in _filas_de_la_matriz(ruta):
        xpath = fila.get("XPath UBL 2.1", "")
        if not xpath.startswith(f"/{nombre}/"):
            continue
        nodos = raiz.xpath(xpath.replace(f"/{nombre}", f"/doc:{nombre}", 1), namespaces=espacios)
        if not nodos:
            continue  # dato condicional que no aplica a esta venta (ISC, cuotas, notas…)
        valores = [_texto(n) for n in nodos]
        valor = " · ".join(valores[:_MAXIMO_VALORES])
        if len(valores) > _MAXIMO_VALORES:
            valor += f" (+{len(valores) - _MAXIMO_VALORES})"
        resultado.append(FilaMatriz(fila["ID"], fila["Dato"], fila["Norma / catálogo"], fila["SUNAT"] == "O",
                                    xpath, valor))
    return resultado
