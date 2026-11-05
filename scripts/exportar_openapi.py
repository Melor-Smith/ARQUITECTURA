"""Regenera specs/contracts/openapi.yaml desde el código (FastAPI + Pydantic).

Uso:  python scripts/exportar_openapi.py
La prueba tests/acceptance/test_contrato.py falla si el archivo queda desactualizado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.adapters.inbound.http.app import crear_app  # noqa: E402
from src.bootstrap import construir_contenedor  # noqa: E402
from src.config import Configuracion  # noqa: E402


def main() -> None:
    esquema = crear_app(construir_contenedor(Configuracion())).openapi()
    destino = RAIZ / "specs" / "contracts" / "openapi.yaml"
    encabezado = "# GENERADO desde el código con scripts/exportar_openapi.py. No editar a mano.\n"
    destino.write_text(encabezado + yaml.safe_dump(esquema, sort_keys=False, allow_unicode=True, width=120),
                       encoding="utf-8")
    print(f"OpenAPI exportado a {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
