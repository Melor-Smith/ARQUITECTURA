"""Autenticación Bearer y autorización por alcances (scopes).

* Sin token o con un token desconocido: 401 con ``WWW-Authenticate``.
* Token válido pero sin el alcance que pide la operación: 403.

Los tokens vienen de la configuración (``ABC_API_TOKENS``). Sustituir este esquema por
OAuth2/JWT no cambia nada fuera de este archivo.
"""

from __future__ import annotations

import hmac

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False, description="Token de acceso. En desarrollo: dev-facturador, dev-almacen "
                                                   "o dev-consulta.")


class NoAutenticado(Exception):
    pass


class SinPermiso(Exception):
    pass


def requiere(alcance: str):
    def _verificar(request: Request, credenciales: HTTPAuthorizationCredentials | None = Security(_bearer)) -> str:
        if credenciales is None:
            raise NoAutenticado("Falta la cabecera 'Authorization: Bearer <token>'.")
        tokens: dict[str, frozenset[str]] = request.app.state.contenedor.configuracion.tokens
        # Comparación en tiempo constante para no filtrar información por temporización.
        alcances = next((a for t, a in tokens.items() if hmac.compare_digest(t, credenciales.credentials)), None)
        if alcances is None:
            raise NoAutenticado("El token de acceso no es válido.")
        if alcance not in alcances:
            raise SinPermiso(f"El token no tiene el alcance '{alcance}' que requiere esta operación.")
        return alcance

    return Depends(_verificar)
