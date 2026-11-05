"""Punto de entrada del instalador MSI (ADR 0008): la misma API, local en la caja Windows.

Levanta ``src.main:app`` en 127.0.0.1 (no se expone a la red de la sucursal) con persistencia
SQLite en ``%LOCALAPPDATA%\\ABC Facturacion\\abc.db``: el núcleo hexagonal es el mismo que corre
en el servidor; solo cambian la configuración y el empaquetado.

Prueba de humo:  abc-facturacion.exe --salud   (levanta, consulta /salud y termina)
"""

from __future__ import annotations

import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

PUERTO = int(os.environ.get("ABC_PUERTO", "8000"))


def _preparar_entorno() -> None:
    datos = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ABC Facturacion"
    datos.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ABC_BASE_DATOS", str(datos / "abc.db"))


def _salud(intentos: int = 60) -> int:
    for _ in range(intentos):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/salud", timeout=2) as respuesta:
                print(respuesta.read().decode("utf-8"))
                return 0
        except OSError:
            time.sleep(1)
    print("La API local no respondió en /salud", file=sys.stderr)
    return 1


def main() -> int:
    _preparar_entorno()
    import uvicorn

    from src.main import app

    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PUERTO, log_level="info"))
    if "--salud" not in sys.argv:
        servidor.run()
        return 0
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    codigo = _salud()
    servidor.should_exit = True
    hilo.join(timeout=10)
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
