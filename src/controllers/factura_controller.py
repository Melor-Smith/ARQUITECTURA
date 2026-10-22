"""src/controllers/factura_controller.py

Controlador para la gestión de Facturas UBL 2.1 y Migración Legado.
Capa de Controlador en MVC desacoplado. Orquesta DTOs, Servicios y Presentadores.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from src.models.schemas import (
    ErrorResponse,
    FacturaRequest,
    FacturaResponse,
    FichaLegadoRequest,
    FichaMigradaResponse,
)
from src.services.sunat_ubl_service import SunatUBLService
from src.views.presenters import FacturaPresenter

router = APIRouter(prefix="/api/v1", tags=["Facturacion UBL 2.1 y Migracion Legado"])


@router.post(
    "/facturas",
    status_code=status.HTTP_201_CREATED,
    response_model=FacturaResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Emite una Factura Electrónica validada contra UBL-Invoice-2.1.xsd y Catálogo 8 SUNAT"
)
def emitir_factura(payload: FacturaRequest):
    """Caso de Uso: Emisión de Comprobante de Pago Electrónico UBL 2.1."""
    try:
        data_dict = payload.model_dump()
        resultado = SunatUBLService.emitir_factura(data_dict)
        return FacturaPresenter.formatear_emision_exitosa(resultado)
    except ValueError as e:
        msg = str(e)
        codigo = "ERR-SUNAT-VALIDACION"
        if "RUC" in msg:
            codigo = "ERR-SUNAT-RUC"
        elif "Catálogo 08" in msg or "ISC" in msg:
            codigo = "ERR-SUNAT-CAT08"
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=FacturaPresenter.formatear_error(codigo, msg),
        )


@router.get(
    "/facturas/{id_comprobante}",
    status_code=status.HTTP_200_OK,
    response_model=FacturaResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Consulta trazabilidad y XML UBL de un comprobante emitido"
)
def consultar_factura(id_comprobante: str):
    """Caso de Uso: Consulta y recuperación de constancia de recepción (CDR) y XML."""
    factura = SunatUBLService.consultar_factura(id_comprobante)
    if not factura:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=FacturaPresenter.formatear_error(
                codigo="ERR-NOT-FOUND",
                mensaje=f"El comprobante '{id_comprobante}' no fue encontrado en los registros.",
            ),
        )
    return FacturaPresenter.formatear_consulta_exitosa(factura)


@router.post(
    "/migracion/fichas-legado",
    status_code=status.HTTP_201_CREATED,
    response_model=FichaMigradaResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Migra fichas informales del software legado de almacén hacia entidades trazables UBL"
)
def migrar_ficha_legado(payload: FichaLegadoRequest):
    """Caso de Uso: Migración de Ficha Histórica de Almacén hacia Comprobante Formal UBL."""
    try:
        data_dict = payload.model_dump()
        resultado = SunatUBLService.migrar_ficha_legado(data_dict)
        return FacturaPresenter.formatear_migracion_exitosa(resultado)
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=FacturaPresenter.formatear_error("ERR-LEGADO-SIN-MOVIMIENTO", str(e)),
        )
