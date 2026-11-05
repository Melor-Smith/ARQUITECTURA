"""Controlador de inventario: migración del sistema antiguo y Kardex."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Body, Path, Query, Request, Response

from src.adapters.inbound.http.esquemas import (
    FichaLegadoEntrada,
    KardexSalida,
    LoteEntrada,
    LoteSalida,
    MigracionSalida,
)
from src.adapters.inbound.http.openapi import ejemplos_openapi, respuestas
from src.adapters.inbound.http.seguridad import requiere
from src.adapters.inbound.http.vistas.inventario import kardex_json, lote_json, migracion_json
from src.application.comandos import MigrarFichaLegadoCmd
from src.bootstrap import Contenedor

router = APIRouter(prefix="/api/v1/inventario", tags=["Inventario y migración"])


def _contenedor(request: Request) -> Contenedor:
    return request.app.state.contenedor


@router.post(
    "/migraciones",
    status_code=201,
    response_model=MigracionSalida,
    dependencies=[requiere("inventario:escribir")],
    summary="Migra una ficha del sistema antiguo al inventario permanente (formato 12.1)",
    description=(
        "Homologa la glosa libre con un producto del catálogo (con factor de conversión de unidades), tipifica "
        "el movimiento (tabla 12) y el documento de soporte (tabla 10: 00 = documento interno) y lo registra en "
        "el Kardex validando el saldo. El vale interno NO se convierte en un número SUNAT."
    ),
    responses=respuestas(400, 401, 403, 409, 422),
)
def migrar_ficha(
    cuerpo: Annotated[FichaLegadoEntrada, Body(openapi_examples=ejemplos_openapi(
        salida_por_venta="ficha-legado-salida.json", ingreso_por_compra="ficha-legado-ingreso.json"))],
    request: Request,
    response: Response,
) -> MigracionSalida:
    migracion = _contenedor(request).migrar_ficha_legado.ejecutar(_comando(cuerpo))
    response.headers["Location"] = f"/api/v1/inventario/migraciones/{quote(migracion.identificador)}"
    return migracion_json(migracion)


def _comando(cuerpo: FichaLegadoEntrada) -> MigrarFichaLegadoCmd:
    return MigrarFichaLegadoCmd(
        fecha=cuerpo.fecha, ingreso=cuerpo.ingreso, salida=cuerpo.salida, producto=cuerpo.producto,
        nro_documento=cuerpo.nro_documento, codigo_producto=cuerpo.codigo_producto,
        factor_conversion=cuerpo.factor_conversion, tipo_operacion=cuerpo.tipo_operacion,
        establecimiento=cuerpo.establecimiento,
    )


@router.post(
    "/migraciones/lotes",
    status_code=201,
    response_model=LoteSalida,
    dependencies=[requiere("inventario:escribir")],
    summary="Migra un lote completo de fichas del sistema antiguo, con observaciones y conciliación",
    description=(
        "Ordena las fichas por fecha, migra cada una con las mismas reglas que la migración individual y NO se "
        "detiene ante una falla: la ficha queda `OBSERVADA` con su código de error, para corregirla y reenviarla. "
        "Las fichas ya migradas quedan `DUPLICADA` (reprocesar el archivo es seguro). Al final concilia por "
        "producto saldo inicial + entradas − salidas contra el saldo final del Kardex."
    ),
    responses=respuestas(400, 401, 403),
)
def migrar_lote(
    cuerpo: Annotated[LoteEntrada, Body(openapi_examples=ejemplos_openapi(
        lote_del_sistema_antiguo="lote-fichas-legado.json"))],
    request: Request,
    response: Response,
) -> LoteSalida:
    lote = _contenedor(request).migrar_lote_legado.ejecutar([_comando(f) for f in cuerpo.fichas])
    response.headers["Location"] = f"/api/v1/inventario/migraciones/lotes/{lote.id}"
    return lote_json(lote)


@router.get(
    "/migraciones/lotes/{id_lote}",
    response_model=LoteSalida,
    dependencies=[requiere("inventario:leer")],
    summary="Consulta el resultado de un lote de migración",
    responses=respuestas(401, 403, 404),
)
def consultar_lote(id_lote: Annotated[str, Path(max_length=20)], request: Request) -> LoteSalida:
    return lote_json(_contenedor(request).consultar_lote.ejecutar(id_lote))


@router.get(
    "/migraciones/{nro_documento}",
    response_model=MigracionSalida,
    dependencies=[requiere("inventario:leer")],
    summary="Consulta la migración de un documento del sistema antiguo",
    responses=respuestas(401, 403, 404),
)
def consultar_migracion(nro_documento: Annotated[str, Path(max_length=40)], request: Request) -> MigracionSalida:
    return migracion_json(_contenedor(request).consultar_migracion.ejecutar(nro_documento))


@router.get(
    "/kardex/{codigo_producto}",
    response_model=KardexSalida,
    dependencies=[requiere("inventario:leer")],
    summary="Kardex en unidades físicas de un producto, con saldo final",
    responses=respuestas(400, 401, 403, 404),
)
def consultar_kardex(
    codigo_producto: Annotated[str, Path(max_length=30, pattern=r"^[A-Z0-9-]+$")],
    request: Request,
    establecimiento: Annotated[str | None, Query(pattern=r"^\d{4}$")] = None,
) -> KardexSalida:
    return kardex_json(_contenedor(request).consultar_kardex.ejecutar(codigo_producto, establecimiento))
