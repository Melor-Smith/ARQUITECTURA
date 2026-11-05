"""Genera el paquete para validar los TXT con el programa PLE de SUNAT.

Uso:  python scripts/preparar_validacion_ple.py   →   docs/evidencia-ple/paquete/

Todo lo que produce el sistema se genera aquí ejecutando la API con un reloj fijo, sin
editar archivos a mano. La única excepción es el Registro de Compras 8.1 con una compra:
el sistema no lleva compras, pero el PLE exige presentarlo junto al 14.1. Va como insumo
de prueba, declarado como tal.

Cada carpeta se carga completa en *Validar Libros Electrónicos* del PLE. El procedimiento
está en ``docs/evidencia-ple/README.md``.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fastapi.testclient import TestClient  # noqa: E402

from src.adapters.inbound.http.app import crear_app  # noqa: E402
from src.adapters.outbound.reloj import ZONA_PERU, RelojFijo  # noqa: E402
from src.bootstrap import construir_contenedor  # noqa: E402
from src.config import Configuracion  # noqa: E402

EJEMPLOS = RAIZ / "specs" / "ejemplos"
DESTINO = RAIZ / "docs" / "evidencia-ple" / "paquete"
CABECERAS = {"Authorization": "Bearer dev-facturador"}
RUC = "20556677884"

#: Comprobantes que no dependen de fichas del sistema antiguo (sirven para cualquier periodo).
COMPROBANTES = ("factura.json", "factura-isc-icbper.json", "factura-credito.json", "boleta.json",
                "nota-credito.json", "nota-debito.json")

#: Registro de Compras 8.1, 42 campos (Anexo 2): la factura física 0001-4587 del proveedor de
#: arroz del caso. Insumo de prueba, no lo genera el sistema.
_COMPRA_8_1 = ["{periodo}", "C{aaaamm}000001", "M1", "{fecha}", "", "01", "0001", "", "4587", "",
               "6", "20601234565", "MOLINO ARROCERO DEL NORTE S.A.C.",
               "3000.00", "540.00", "0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "3540.00",
               "PEN", "1.000", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "1"]


def _cargar(nombre: str) -> dict:
    return json.loads((EJEMPLOS / nombre).read_text(encoding="utf-8"))


def _libro(cliente: TestClient, ruta: str, periodo: str) -> tuple[str, bytes]:
    r = cliente.get(f"/api/v1/libros-electronicos/{ruta}/{periodo}", headers=CABECERAS)
    r.raise_for_status()
    return r.headers["content-disposition"].split('filename="')[1].rstrip('"').replace(".txt", ".TXT"), r.content


def _compras_vacias(periodo: str) -> dict[str, bytes]:
    """8.1 y 8.2 sin información: nombre con indicador de contenido 0 y archivo vacío."""
    return {f"LE{RUC}{periodo}00{libro}001011.TXT": b"" for libro in ("080100", "080200")}


def _compra_de_prueba(periodo: str, fecha: str) -> dict[str, bytes]:
    campos = [c.format(periodo=f"{periodo}00", aaaamm=periodo, fecha=fecha) for c in _COMPRA_8_1]
    assert len(campos) == 42
    return {f"LE{RUC}{periodo}00080100001111.TXT": ("|".join(campos) + "|\r\n").encode("utf-8"),
            f"LE{RUC}{periodo}00080200001011.TXT": b""}


def _servidor(momento: dt.datetime) -> tuple[TestClient, object]:
    """El inventario inicial se carga el día 1 del mes simulado (fecha de corte)."""
    contenedor = construir_contenedor(Configuracion(), reloj=RelojFijo(momento.replace(tzinfo=ZONA_PERU)),
                                      fecha_inventario_inicial=momento.date().replace(day=1))
    return TestClient(crear_app(contenedor)), contenedor


def paquete() -> dict[str, bytes]:
    """{ruta relativa: contenido} de todo el paquete. Determinista: mismo código, mismos bytes."""
    archivos: dict[str, bytes] = {}

    # Octubre de 2026: el flujo completo del caso (como scripts/generar_ejemplos.py).
    cliente, contenedor = _servidor(dt.datetime(2026, 10, 22, 10, 30))
    for ficha in ("ficha-legado-salida.json", "ficha-legado-ingreso.json"):
        cliente.post("/api/v1/inventario/migraciones", json=_cargar(ficha), headers=CABECERAS).raise_for_status()
    cliente.post("/api/v1/inventario/migraciones/lotes", json=_cargar("lote-fichas-legado.json"),
                 headers=CABECERAS).raise_for_status()
    for nombre in ("factura.json", "factura-isc-icbper.json", "factura-credito.json", "factura-de-vale-legado.json",
                   "boleta.json", "nota-credito.json", "nota-debito.json"):
        cliente.post("/api/v1/comprobantes", json=_cargar(nombre), headers=CABECERAS).raise_for_status()
    nombre, contenido = _libro(cliente, "inventario-unidades-fisicas", "202610")
    archivos[f"12.1-octubre-2026/{nombre}"] = contenido
    nombre, contenido = _libro(cliente, "registro-ventas", "202610")
    archivos[f"14.1-octubre-2026/{nombre}"] = contenido
    archivos.update({f"14.1-octubre-2026/{n}": c for n, c in _compras_vacias("202610").items()})
    contenedor.cerrar()  # type: ignore[attr-defined]

    # Marzo de 2022: anterior al corte del RVIE (PER_CORTE_RVIE_TODOS = 20220400 en el PLE 5.2.0.7).
    cliente, contenedor = _servidor(dt.datetime(2022, 3, 22, 10, 30))
    for nombre in COMPROBANTES:
        cliente.post("/api/v1/comprobantes", json=_cargar(nombre), headers=CABECERAS).raise_for_status()
    nombre, contenido = _libro(cliente, "registro-ventas", "202203")
    archivos[f"14.1-marzo-2022/{nombre}"] = contenido
    archivos.update({f"14.1-marzo-2022/{n}": c for n, c in _compra_de_prueba("202203", "20/03/2022").items()})
    contenedor.cerrar()  # type: ignore[attr-defined]
    return archivos


def main() -> None:
    for ruta, contenido in paquete().items():
        destino = DESTINO / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
    print(f"Paquete de validación PLE generado en {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
