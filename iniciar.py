"""Lanzador: abre el formulario "Registrar venta" (Taller 2) con un solo comando.

    python iniciar.py            (Windows: doble clic en iniciar.bat)

Solo necesita Python 3.10 o superior. La primera vez crea el entorno ``.venv`` e instala
``requirements.txt`` (alrededor de un minuto); las siguientes veces arranca directo. Luego levanta
el servidor en este equipo (127.0.0.1, no se expone a la red) y abre el navegador en ``/venta``.
Para detenerlo: Ctrl+C o cerrar la ventana.

Usa solo la biblioteca estándar, para poder ejecutarse antes de instalar nada.
"""

from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENTORNO = RAIZ / ".venv"
REQUISITOS = RAIZ / "requirements.txt"
MARCA = ENTORNO / ".requisitos-instalados"
VERSION_MINIMA = (3, 10)
PUERTO_PREFERIDO = 8000


def version_soportada(version: tuple[int, ...] = tuple(sys.version_info[:2])) -> bool:
    return version >= VERSION_MINIMA


def python_del_entorno(entorno: Path = ENTORNO) -> Path:
    return entorno / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def huella_requisitos(requisitos: Path = REQUISITOS) -> str:
    return hashlib.sha256(requisitos.read_bytes()).hexdigest()


def necesita_instalar(marca: Path = MARCA, requisitos: Path = REQUISITOS) -> bool:
    """Se instala la primera vez o cuando cambia ``requirements.txt``."""
    return not marca.exists() or marca.read_text(encoding="utf-8").strip() != huella_requisitos(requisitos)


def puerto_libre(preferido: int = PUERTO_PREFERIDO, intentos: int = 20) -> int:
    for puerto in range(preferido, preferido + intentos):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", puerto)) != 0:  # nadie escucha en ese puerto
                return puerto
    raise RuntimeError(f"No hay un puerto libre entre {preferido} y {preferido + intentos - 1}.")


def preparar_entorno() -> Path:
    python = python_del_entorno()
    if not python.exists():
        print("Creando el entorno .venv (solo la primera vez)...")
        venv.EnvBuilder(with_pip=True).create(ENTORNO)
    if necesita_instalar():
        print("Instalando dependencias de requirements.txt (solo la primera vez, ~1 minuto)...")
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r",
                        str(REQUISITOS)], check=True)
        MARCA.write_text(huella_requisitos(), encoding="utf-8")
    return python


def esperar_servidor(url: str, proceso: subprocess.Popen, segundos: int = 60) -> bool:
    for _ in range(segundos * 2):
        if proceso.poll() is not None:
            return False  # el servidor terminó con error
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):  # mensajes inmediatos también fuera de una consola interactiva
        sys.stdout.reconfigure(line_buffering=True)
    if not version_soportada():
        print(f"Se necesita Python {VERSION_MINIMA[0]}.{VERSION_MINIMA[1]} o superior; este es "
              f"{sys.version.split()[0]}. Descárguelo de https://www.python.org/downloads/", file=sys.stderr)
        return 1
    python = preparar_entorno()
    puerto = puerto_libre()
    base = f"http://127.0.0.1:{puerto}"
    print(f"Iniciando el servidor en {base} ...")
    proceso = subprocess.Popen([str(python), "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1",
                                "--port", str(puerto)], cwd=RAIZ)
    try:
        if not esperar_servidor(f"{base}/salud", proceso):
            print("El servidor no pudo iniciar. Revise los mensajes de arriba.", file=sys.stderr)
            return 1
        print(f"\n  Formulario 'Registrar venta': {base}/venta")
        print(f"  API (Swagger):                {base}/docs")
        print("\n  Para detener el servidor: Ctrl+C o cierre esta ventana.\n")
        if not os.environ.get("ABC_SIN_NAVEGADOR"):  # p. ej. en una prueba automática
            webbrowser.open(f"{base}/venta")
        return proceso.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if proceso.poll() is None:
            proceso.terminate()
            proceso.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
