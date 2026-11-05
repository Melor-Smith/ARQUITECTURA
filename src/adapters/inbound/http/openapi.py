"""Ayudas para que el OpenAPI generado describa fielmente lo que hace la API."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from src.adapters.inbound.http.esquemas import Problema

DIRECTORIO_EJEMPLOS = Path(__file__).resolve().parents[4] / "specs" / "ejemplos"

_DESCRIPCIONES = {
    400: "La solicitud no cumple el esquema del contrato (tipos, formatos, catálogos, campos no permitidos).",
    401: "Falta el token Bearer o no es válido.",
    403: "El token no tiene el alcance requerido.",
    404: "El recurso no existe.",
    409: "Conflicto: recurso duplicado, clave de idempotencia reutilizada o estado incompatible.",
    422: "La solicitud cumple el esquema, pero viola una regla de negocio o normativa SUNAT.",
    502: "La OSE respondió algo que no es un CDR válido.",
    503: "La OSE no está disponible; reintente después del tiempo indicado en Retry-After.",
}


def respuestas(*codigos: int) -> dict[int | str, dict[str, Any]]:
    return {c: {"model": Problema, "description": _DESCRIPCIONES[c]} for c in codigos}


@cache
def ejemplo(nombre: str) -> dict[str, Any]:
    return json.loads((DIRECTORIO_EJEMPLOS / nombre).read_text(encoding="utf-8"))


def ejemplos_openapi(**archivos: str) -> dict[str, dict[str, Any]]:
    return {clave: {"summary": clave.replace("_", " ").capitalize(), "value": ejemplo(archivo)}
            for clave, archivo in archivos.items()}


def instalar_openapi(app: FastAPI) -> None:
    """Los errores se declaran como ``application/problem+json`` y se quitan los esquemas de
    validación por defecto de FastAPI, que esta API no devuelve."""

    def generar() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        esquema = get_openapi(title=app.title, version=app.version, description=app.description,
                              routes=app.routes, tags=app.openapi_tags)
        for operaciones in esquema.get("paths", {}).values():
            for operacion in operaciones.values():
                respuestas_op = operacion.get("responses", {})
                # FastAPI agrega un 422 genérico; aquí los errores de formato son 400 (ver problemas.py).
                generico = respuestas_op.get("422", {}).get("content", {}).get("application/json", {})
                if generico.get("schema", {}).get("$ref", "").endswith("/HTTPValidationError"):
                    del respuestas_op["422"]
                for codigo, respuesta in respuestas_op.items():
                    contenido = respuesta.get("content", {})
                    if codigo.isdigit() and int(codigo) >= 400 and "application/json" in contenido:
                        contenido["application/problem+json"] = contenido.pop("application/json")
        componentes = esquema.get("components", {}).get("schemas", {})
        texto = json.dumps(esquema.get("paths", {}))
        for sobrante in ("HTTPValidationError", "ValidationError"):
            if f"#/components/schemas/{sobrante}" not in texto:
                componentes.pop(sobrante, None)
        app.openapi_schema = esquema
        return esquema

    app.openapi = generar  # type: ignore[method-assign]
