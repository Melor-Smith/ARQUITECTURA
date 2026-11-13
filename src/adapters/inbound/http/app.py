"""Fábrica de la aplicación FastAPI (adaptador de entrada HTTP)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from src.adapters.inbound.http.controladores import comprobantes, inventario, libros, venta
from src.adapters.inbound.http.esquemas import Salud
from src.adapters.inbound.http.openapi import instalar_openapi
from src.adapters.inbound.http.problemas import registrar_manejadores
from src.bootstrap import Contenedor, construir_contenedor

VERSION = "2.0.0"

DESCRIPCION = """
API de facturación electrónica UBL 2.1 (SUNAT) e inventario de **ABC Software Corp**.

* Comprobantes: factura (01), boleta (03), nota de crédito (07) y nota de débito (08).
* El servidor calcula IGV, ISC (Catálogo 08) e ICBPER y asigna el correlativo; el cliente no envía montos de
  impuestos.
* XML generado desde clases del XSD OASIS UBL 2.1, validado y firmado con XMLDSig.
* Migración de fichas del sistema antiguo al inventario permanente y libros electrónicos PLE 14.1 y 12.1.
* Errores en `application/problem+json` (RFC 9457): 400 contrato, 422 regla de negocio, 409 conflicto.

El contrato se escribe primero (spec-first, ADR 0013): `specs/contracts/openapi.yaml` y los JSON Schemas de
`specs/contracts/schemas/`. Este documento lo publica el código que lo implementa y una prueba falla si se apartan.
"""

ETIQUETAS = [
    {"name": "Comprobantes", "description": "Emisión, consulta, XML y reenvío a la OSE."},
    {"name": "Inventario y migración", "description": "Fichas del sistema antiguo, Kardex y saldos."},
    {"name": "Libros electrónicos (PLE)", "description": "Formatos 14.1 y 12.1."},
    {"name": "Salud", "description": "Estado del servicio."},
]


def crear_app(contenedor: Contenedor | None = None) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.contenedor.cerrar()  # cierra la base de datos al apagar el servicio

    app = FastAPI(
        lifespan=ciclo_de_vida,
        title="ABC Software Corp - Facturación electrónica UBL 2.1 e inventario",
        version=VERSION,
        description=DESCRIPCION,
        openapi_tags=ETIQUETAS,
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.contenedor = contenedor or construir_contenedor()
    registrar_manejadores(app)
    app.include_router(comprobantes.router)
    app.include_router(inventario.router)
    app.include_router(libros.router)
    app.include_router(venta.router)  # vista HTML del Taller 2 (/venta); no es parte de la API /api/v1

    @app.get("/salud", response_model=Salud, tags=["Salud"], summary="Estado del servicio")
    def salud(request: Request) -> Salud:
        configuracion = request.app.state.contenedor.configuracion
        return Salud(estado="OPERATIVO", version=VERSION, version_ubl="2.1", modo_ose=configuracion.modo_ose.value)

    instalar_openapi(app)
    return app
