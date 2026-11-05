"""Configuración por variables de entorno (12-factor)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from src.adapters.outbound.ose.simulada import ModoOse
from src.adapters.outbound.ose.sunat_soap import CLAVE_BETA, ENDPOINT_BETA, ENDPOINT_PRODUCCION, USUARIO_BETA

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


def es_token_de_desarrollo(token: str) -> bool:
    """Un token ``dev-*`` es público (está en el README y en este archivo): nunca vale en producción."""
    return token in TOKENS_DESARROLLO or token.startswith("dev-")


@dataclass(frozen=True)
class Configuracion:
    modo_ose: ModoOse = ModoOse.NORMAL
    plazo_envio_dias: int = 3
    tokens: dict[str, frozenset[str]] = field(default_factory=lambda: dict(TOKENS_DESARROLLO))
    certificado_pfx: Path | None = None
    contrasena_certificado: str = ""
    #: Ruta del archivo SQLite. Sin valor, la persistencia es en memoria (desarrollo y pruebas).
    base_datos: Path | None = None
    #: URL del servicio ``billService`` de SUNAT. Sin valor se usa la OSE simulada.
    #: ``ABC_SUNAT_ENDPOINT=beta`` es atajo del entorno de pruebas de SUNAT (ver ADR 0012).
    sunat_endpoint: str | None = None
    sunat_usuario_sol: str = USUARIO_BETA
    sunat_clave_sol: str = CLAVE_BETA

    def __post_init__(self) -> None:
        if self.sunat_endpoint != ENDPOINT_PRODUCCION:
            return
        if self.certificado_pfx is None or self.sunat_usuario_sol == USUARIO_BETA:
            raise ValueError("Producción SUNAT exige ABC_CERTIFICADO_PFX y un usuario SOL secundario real: "
                             "el certificado autofirmado y MODDATOS solo valen en beta.")
        if not self.tokens:
            raise ValueError("Producción exige al menos un token propio en ABC_API_TOKENS.")
        if any(es_token_de_desarrollo(token) for token in self.tokens):
            raise ValueError("Producción no admite los tokens de desarrollo dev-*: defina ABC_API_TOKENS "
                             "con tokens propios (ver ADR 0005).")

    @classmethod
    def desde_entorno(cls) -> Configuracion:
        tokens_json = os.environ.get("ABC_API_TOKENS")
        tokens = (
            {token: frozenset(alcances) for token, alcances in json.loads(tokens_json).items()}
            if tokens_json else dict(TOKENS_DESARROLLO)
        )
        pfx = os.environ.get("ABC_CERTIFICADO_PFX")
        endpoint = os.environ.get("ABC_SUNAT_ENDPOINT")
        return cls(
            modo_ose=ModoOse(os.environ.get("ABC_MODO_OSE", ModoOse.NORMAL.value)),
            plazo_envio_dias=int(os.environ.get("ABC_PLAZO_ENVIO_DIAS", "3")),
            tokens=tokens,
            certificado_pfx=Path(pfx) if pfx else None,
            contrasena_certificado=os.environ.get("ABC_CERTIFICADO_CONTRASENA", ""),
            base_datos=Path(os.environ["ABC_BASE_DATOS"]) if os.environ.get("ABC_BASE_DATOS") else None,
            sunat_endpoint=_ATAJOS_ENDPOINT.get(endpoint, endpoint) if endpoint else None,
            sunat_usuario_sol=os.environ.get("ABC_SUNAT_USUARIO_SOL", USUARIO_BETA),
            sunat_clave_sol=os.environ.get("ABC_SUNAT_CLAVE_SOL", CLAVE_BETA),
        )


_ATAJOS_ENDPOINT = {"beta": ENDPOINT_BETA, "produccion": ENDPOINT_PRODUCCION}
