"""Configuración por variables de entorno (12-factor)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from src.adapters.outbound.ose.simulada import ModoOse

ALCANCES = (
    "comprobantes:emitir",
    "comprobantes:leer",
    "inventario:escribir",
    "inventario:leer",
    "libros:leer",
)

#: Tokens SOLO para desarrollo local. En producción se definen con ABC_API_TOKENS o se
#: reemplaza el esquema por OAuth2/JWT (ver ADR 0005).
TOKENS_DESARROLLO: dict[str, frozenset[str]] = {
    "dev-facturador": frozenset(ALCANCES),
    "dev-almacen": frozenset({"inventario:escribir", "inventario:leer"}),
    "dev-consulta": frozenset({"comprobantes:leer", "inventario:leer", "libros:leer"}),
}


@dataclass(frozen=True)
class Configuracion:
    modo_ose: ModoOse = ModoOse.NORMAL
    plazo_envio_dias: int = 3
    tokens: dict[str, frozenset[str]] = field(default_factory=lambda: dict(TOKENS_DESARROLLO))
    certificado_pfx: Path | None = None
    contrasena_certificado: str = ""
    #: Ruta del archivo SQLite. Sin valor, la persistencia es en memoria (desarrollo y pruebas).
    base_datos: Path | None = None

    @classmethod
    def desde_entorno(cls) -> Configuracion:
        tokens_json = os.environ.get("ABC_API_TOKENS")
        tokens = (
            {token: frozenset(alcances) for token, alcances in json.loads(tokens_json).items()}
            if tokens_json else dict(TOKENS_DESARROLLO)
        )
        pfx = os.environ.get("ABC_CERTIFICADO_PFX")
        return cls(
            modo_ose=ModoOse(os.environ.get("ABC_MODO_OSE", ModoOse.NORMAL.value)),
            plazo_envio_dias=int(os.environ.get("ABC_PLAZO_ENVIO_DIAS", "3")),
            tokens=tokens,
            certificado_pfx=Path(pfx) if pfx else None,
            contrasena_certificado=os.environ.get("ABC_CERTIFICADO_CONTRASENA", ""),
            base_datos=Path(os.environ["ABC_BASE_DATOS"]) if os.environ.get("ABC_BASE_DATOS") else None,
        )
