"""src/main.py

Punto de entrada principal ASGI de la aplicación FastAPI.
Configura enrutamiento MVC, manejadores de excepciones normativas y metadatos OpenAPI.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.controllers.factura_controller import router as factura_router

app = FastAPI(
    title="ABC Software Corp - API Facturación UBL 2.1 y Migración Legado (SUNAT)",
    version="1.0.0",
    description=(
        "Especificación Spec-First bajo arquitectura MVC desacoplada (preparada para Arquitectura Hexagonal), "
        "cumpliendo RS N° 097-2012, Catálogo 8 de SUNAT (ISC) y esquema OASIS UBL-Invoice-2.1.xsd."
    ),
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Mapea errores de validación de esquemas hacia el contrato ErrorResponse (HTTP 400)."""
    errors = exc.errors()
    mensajes = []
    codigo = "ERR-SUNAT-VALIDACION"

    for err in errors:
        loc = ".".join(str(p) for p in err.get("loc", []))
        msg = err.get("msg", "")
        mensajes.append(f"Campo '{loc}': {msg}")

        # Trazabilidad de códigos normativos específicos
        loc_lower = loc.lower()
        msg_lower = msg.lower()
        if "ruc" in loc_lower or "ruc" in msg_lower:
            codigo = "ERR-SUNAT-RUC"
        elif "codigo_sistema_isc" in loc_lower or "isc" in loc_lower or "catálogo 08" in msg_lower:
            codigo = "ERR-SUNAT-CAT08"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "codigo": codigo,
            "mensaje": f"Error de validación normativa: {'; '.join(mensajes)}",
        },
    )


# Registrar controladores (Rutas MVC)
app.include_router(factura_router)


@app.get("/", tags=["Health"])
def health_check():
    """Endpoint de estado del servicio."""
    return {
        "sistema": "ABC Software Corp - Facturación Electrónica UBL 2.1",
        "estado": "OPERACIONAL",
        "version_ubl": "2.1",
        "normativa": "SUNAT RS 097-2012 / Catálogo 08 ISC",
    }
