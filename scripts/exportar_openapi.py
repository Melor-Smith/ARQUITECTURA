"""Compara el contrato escrito a mano con lo que implementa el código (ADR 0013).

Uso:
    python scripts/exportar_openapi.py            # lista las diferencias; código de salida 1 si hay
    python scripts/exportar_openapi.py --guardar  # además guarda el OpenAPI del código en build/

Ya **no genera** ``specs/contracts/openapi.yaml``: ese archivo y ``specs/contracts/schemas/`` se
escriben a mano y se cambian primero. Esta herramienta dice qué le falta al código para cumplirlos
(la misma comparación que hace ``tests/acceptance/test_contrato.py`` en la CI).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.contrato import Contrato, diferencias  # noqa: E402
from src.adapters.inbound.http.app import crear_app  # noqa: E402
from src.bootstrap import construir_contenedor  # noqa: E402
from src.config import Configuracion  # noqa: E402

DESTINO = RAIZ / "build" / "openapi-desde-el-codigo.yaml"


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--guardar", action="store_true", help=f"guarda el OpenAPI del código en {DESTINO.name}")
    opciones = parser.parse_args(argumentos)

    codigo = crear_app(construir_contenedor(Configuracion())).openapi()
    if opciones.guardar:
        DESTINO.parent.mkdir(exist_ok=True)
        DESTINO.write_text(yaml.safe_dump(codigo, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
        print(f"OpenAPI del código guardado en {DESTINO.relative_to(RAIZ)} (solo para comparar; no es el contrato)")

    encontradas = diferencias(Contrato().empaquetado(), codigo)
    if not encontradas:
        print("El código implementa exactamente el contrato de specs/contracts.")
        return 0
    print(f"{len(encontradas)} diferencia(s) entre el contrato (manda) y el código:")
    for diferencia in encontradas:
        print(f"  - {diferencia}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
