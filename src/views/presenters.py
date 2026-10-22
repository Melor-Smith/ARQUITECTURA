"""src/views/presenters.py

Presentadores y formateadores de vistas (Capa de Vista en MVC).
Asegura que las salidas JSON/XML correspondan rigurosamente con los contratos OpenAPI.
"""

from typing import Any, Dict
from src.models.schemas import ErrorResponse, FacturaResponse, FichaMigradaResponse


class FacturaPresenter:
    """Presentador para comprobantes electrónicos UBL 2.1."""

    @staticmethod
    def formatear_emision_exitosa(data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea y valida la respuesta para el caso de emisión exitosa (201)."""
        response_dto = FacturaResponse.model_validate(data)
        return response_dto.model_dump()

    @staticmethod
    def formatear_consulta_exitosa(data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea y valida la respuesta de consulta de comprobante (200)."""
        response_dto = FacturaResponse.model_validate(data)
        return response_dto.model_dump()

    @staticmethod
    def formatear_migracion_exitosa(data: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea y valida la respuesta de migración de ficha histórica (201)."""
        response_dto = FichaMigradaResponse.model_validate(data)
        return response_dto.model_dump()

    @staticmethod
    def formatear_error(codigo: str, mensaje: str) -> Dict[str, Any]:
        """Formatea una respuesta de error normativa o de validación (400/404)."""
        error_dto = ErrorResponse(codigo=codigo, mensaje=mensaje)
        return error_dto.model_dump()
