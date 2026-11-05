"""Traducción de excepciones a ``application/problem+json`` (RFC 9457).

| Origen                                   | HTTP | Significado                                   |
|------------------------------------------|------|-----------------------------------------------|
| ``RequestValidationError`` (Pydantic)    | 400  | No cumple el esquema del contrato             |
| ``NoAutenticado``                        | 401  | Falta el token o es inválido                  |
| ``SinPermiso``                           | 403  | El token no tiene el alcance requerido        |
| ``RecursoNoEncontrado``                  | 404  | No existe                                     |
| ``Conflicto`` / ``ConflictoDominio``     | 409  | Duplicado, idempotencia o estado incompatible |
| ``ErrorDominio``                         | 422  | Cumple el esquema pero viola una regla        |
| ``XmlNoConformeXsd`` / no controlada     | 500  | Defecto interno (no se exponen detalles)      |
| ``OseRespuestaInvalida``                 | 502  | La OSE respondió algo que no es un CDR        |
| ``OseNoDisponible``                      | 503  | La OSE no responde (incluye Retry-After)      |
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.adapters.inbound.http.esquemas import ErrorCampo, Problema
from src.adapters.inbound.http.seguridad import NoAutenticado, SinPermiso
from src.application.errores import (
    Conflicto,
    OseNoDisponible,
    OseRespuestaInvalida,
    RecursoNoEncontrado,
    XmlNoConformeXsd,
)
from src.domain.errores import ConflictoDominio, ErrorDominio

TIPO_CONTENIDO = "application/problem+json"
_ETIQUETAS_DISCRIMINADOR = {"01", "03", "07", "08"}
_log = logging.getLogger("abc.api")


def respuesta_problema(
    request: Request,
    *,
    status: int,
    titulo: str,
    detalle: str,
    codigo: str,
    tipo: str,
    errores: list[ErrorCampo] | None = None,
    cabeceras: dict[str, str] | None = None,
) -> JSONResponse:
    problema = Problema(
        type=f"urn:abc:problema:{tipo}", title=titulo, status=status, detail=detalle,
        instance=str(request.url.path), codigo=codigo, errores=errores or [],
    )
    return JSONResponse(problema.model_dump(mode="json"), status_code=status, media_type=TIPO_CONTENIDO,
                        headers=cabeceras)


def _codigo_para_campo(campo: str, tipo_error: str) -> str:
    """Código de error estable según el campo que no cumple el contrato."""
    if tipo_error == "extra_forbidden":
        return "ERR-CONTRATO-CAMPO-NO-PERMITIDO"
    reglas = (
        ("isc", "ERR-SUNAT-CAT08"),
        ("unidad_medida", "ERR-SUNAT-CAT03"),
        ("afectacion_igv", "ERR-SUNAT-CAT07"),
        ("tipo_documento", "ERR-SUNAT-CAT06"),
        ("motivo", "ERR-SUNAT-MOTIVO-NOTA"),
        ("serie", "ERR-SUNAT-SERIE"),
        ("moneda", "ERR-SUNAT-CAT02"),
    )
    for fragmento, codigo in reglas:
        if fragmento in campo:
            return codigo
    return "ERR-CONTRATO-FORMATO"


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _formato(request: Request, exc: RequestValidationError) -> JSONResponse:
        errores = []
        codigos = []
        for err in exc.errors():
            ubicacion = [str(p) for p in err.get("loc", ())]
            if ubicacion[:1] in (["body"], ["query"], ["path"], ["header"]):
                ubicacion = ubicacion[1:]
            if len(ubicacion) > 1 and ubicacion[0] in _ETIQUETAS_DISCRIMINADOR:
                ubicacion = ubicacion[1:]  # quita la etiqueta "01"/"03"/"07"/"08" de la unión discriminada
            campo = ".".join(ubicacion) or "body"
            errores.append(ErrorCampo(campo=campo, mensaje=err.get("msg", "")))
            codigos.append(_codigo_para_campo(campo, err.get("type", "")))
        codigo = next((c for c in codigos if c != "ERR-CONTRATO-FORMATO"), "ERR-CONTRATO-FORMATO")
        return respuesta_problema(
            request, status=400, titulo="La solicitud no cumple el contrato",
            detalle=f"{len(errores)} campo(s) no cumplen el esquema OpenAPI.", codigo=codigo,
            tipo="contrato", errores=errores,
        )

    @app.exception_handler(NoAutenticado)
    async def _no_autenticado(request: Request, exc: NoAutenticado) -> JSONResponse:
        return respuesta_problema(request, status=401, titulo="No autenticado", detalle=str(exc),
                                  codigo="ERR-AUTH-TOKEN", tipo="no-autenticado",
                                  cabeceras={"WWW-Authenticate": 'Bearer realm="abc-facturacion"'})

    @app.exception_handler(SinPermiso)
    async def _sin_permiso(request: Request, exc: SinPermiso) -> JSONResponse:
        return respuesta_problema(request, status=403, titulo="Permiso insuficiente", detalle=str(exc),
                                  codigo="ERR-AUTH-ALCANCE", tipo="sin-permiso")

    @app.exception_handler(RecursoNoEncontrado)
    async def _no_encontrado(request: Request, exc: RecursoNoEncontrado) -> JSONResponse:
        return respuesta_problema(request, status=404, titulo="Recurso no encontrado", detalle=exc.mensaje,
                                  codigo=exc.codigo, tipo="no-encontrado")

    @app.exception_handler(Conflicto)
    async def _conflicto(request: Request, exc: Conflicto) -> JSONResponse:
        return respuesta_problema(request, status=409, titulo="Conflicto", detalle=exc.mensaje,
                                  codigo=exc.codigo, tipo="conflicto")

    @app.exception_handler(ErrorDominio)
    async def _dominio(request: Request, exc: ErrorDominio) -> JSONResponse:
        errores = [ErrorCampo(campo=exc.campo, mensaje=exc.mensaje)] if exc.campo else []
        if isinstance(exc, ConflictoDominio):
            return respuesta_problema(request, status=409, titulo="Conflicto con el estado actual",
                                      detalle=exc.mensaje, codigo=exc.codigo, tipo="conflicto", errores=errores)
        return respuesta_problema(request, status=422, titulo="Regla de negocio o normativa incumplida",
                                  detalle=exc.mensaje, codigo=exc.codigo, tipo="regla-negocio", errores=errores)

    @app.exception_handler(OseNoDisponible)
    async def _ose_caida(request: Request, exc: OseNoDisponible) -> JSONResponse:
        return respuesta_problema(request, status=503, titulo="OSE no disponible", detalle=exc.mensaje,
                                  codigo=exc.codigo, tipo="ose-no-disponible",
                                  cabeceras={"Retry-After": str(exc.reintentar_en_segundos)})

    @app.exception_handler(OseRespuestaInvalida)
    async def _ose_invalida(request: Request, exc: OseRespuestaInvalida) -> JSONResponse:
        return respuesta_problema(request, status=502, titulo="Respuesta inválida de la OSE", detalle=exc.mensaje,
                                  codigo=exc.codigo, tipo="ose-respuesta-invalida")

    @app.exception_handler(XmlNoConformeXsd)
    async def _xsd(request: Request, exc: XmlNoConformeXsd) -> JSONResponse:
        _log.error("XML UBL no conforme al XSD: %s", exc.errores)
        return respuesta_problema(request, status=500, titulo="Error interno", detalle="El XML generado no pasó "
                                  "la validación XSD; el incidente quedó registrado.", codigo=exc.codigo,
                                  tipo="error-interno")

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return respuesta_problema(request, status=exc.status_code, titulo=str(exc.detail), detalle=str(exc.detail),
                                  codigo=f"ERR-HTTP-{exc.status_code}", tipo="http")

    @app.exception_handler(Exception)
    async def _no_controlada(request: Request, exc: Exception) -> JSONResponse:
        _log.exception("Error no controlado", exc_info=exc)
        return respuesta_problema(request, status=500, titulo="Error interno",
                                  detalle="Ocurrió un error inesperado.", codigo="ERR-INTERNO", tipo="error-interno")
