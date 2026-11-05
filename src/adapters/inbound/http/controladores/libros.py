"""Controlador de libros electrónicos del PLE (formatos 14.1 y 12.1)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request, Response

from src.adapters.inbound.http.esquemas import LibroElectronicoSalida
from src.adapters.inbound.http.openapi import respuestas
from src.adapters.inbound.http.seguridad import requiere
from src.adapters.inbound.http.vistas.ple import libro_json, libro_txt

router = APIRouter(prefix="/api/v1/libros-electronicos", tags=["Libros electrónicos (PLE)"])

PeriodoPath = Annotated[str, Path(pattern=r"^\d{4}(0[1-9]|1[0-2])$", description="AAAAMM", examples=["202610"])]
FormatoQuery = Annotated[Literal["txt", "json"], Query(description="txt = archivo del PLE; json = vista legible.")]

_RESPUESTA_LIBRO = {
    200: {
        "model": LibroElectronicoSalida,
        "description": "Libro del periodo. En TXT, el nombre de archivo PLE va en Content-Disposition.",
        "content": {"text/plain": {"schema": {"type": "string"}}},
    },
    **respuestas(400, 401, 403),
    422: {**respuestas(422)[422], "description": "ERR-PLE-ESTRUCTURA: alguna fila no cumple el Anexo 2 de la "
          "RS 286-2009 (línea, campo y motivo en el detalle); no se entrega un TXT que el PLE rechazaría."},
}


@router.get(
    "/registro-ventas/{periodo}",
    response_class=Response,
    dependencies=[requiere("libros:leer")],
    summary="Formato 14.1: Registro de Ventas e Ingresos",
    responses=_RESPUESTA_LIBRO,
    openapi_extra={"x-formato-ple": "140100"},
)
def registro_ventas(periodo: PeriodoPath, request: Request, formato: FormatoQuery = "txt") -> Response:
    libro = request.app.state.contenedor.registro_ventas_141.ejecutar(periodo)
    if formato == "json":
        return Response(libro_json("14.1", libro).model_dump_json(), media_type="application/json")
    return libro_txt(libro)


@router.get(
    "/inventario-unidades-fisicas/{periodo}",
    response_class=Response,
    dependencies=[requiere("libros:leer")],
    summary="Formato 12.1: Registro del Inventario Permanente en Unidades Físicas",
    responses=_RESPUESTA_LIBRO,
    openapi_extra={"x-formato-ple": "120100"},
)
def inventario_fisico(periodo: PeriodoPath, request: Request, formato: FormatoQuery = "txt") -> Response:
    libro = request.app.state.contenedor.inventario_121.ejecutar(periodo)
    if formato == "json":
        return Response(libro_json("12.1", libro).model_dump_json(), media_type="application/json")
    return libro_txt(libro)
