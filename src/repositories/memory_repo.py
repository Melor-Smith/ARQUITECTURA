"""src/repositories/memory_repo.py

Puerto y adaptador de persistencia en memoria.
Accede exclusivamente a tests/mocks/mock_db.py para cumplir con las Reglas Duras del SDD.
"""

from typing import Any, Dict, List, Optional
from tests.mocks.mock_db import (
    DB_FACTURAS,
    DB_FICHAS_LEGADO,
    DB_MIGRACIONES,
)


class FacturaMemoryRepository:
    """Repositorio en memoria para comprobantes electrónicos UBL 2.1."""

    @staticmethod
    def guardar_factura(id_comprobante: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Almacena una factura emitida en el diccionario en memoria."""
        DB_FACTURAS[id_comprobante] = data
        return DB_FACTURAS[id_comprobante]

    @staticmethod
    def obtener_factura_por_id(id_comprobante: str) -> Optional[Dict[str, Any]]:
        """Recupera una factura emitida por su ID de comprobante (ej: F001-000001)."""
        return DB_FACTURAS.get(id_comprobante)

    @staticmethod
    def listar_facturas() -> List[Dict[str, Any]]:
        """Lista todas las facturas emitidas."""
        return list(DB_FACTURAS.values())

    @staticmethod
    def guardar_migracion(id_migracion: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Almacena una ficha histórica migrada."""
        DB_MIGRACIONES[id_migracion] = data
        return DB_MIGRACIONES[id_migracion]

    @staticmethod
    def obtener_migracion_por_id(id_migracion: str) -> Optional[Dict[str, Any]]:
        """Recupera una migración por su identificador."""
        return DB_MIGRACIONES.get(id_migracion)

    @staticmethod
    def obtener_fichas_legado() -> List[Dict[str, Any]]:
        """Obtiene la lista de registros históricos informales del almacén legado."""
        return list(DB_FICHAS_LEGADO)

    @staticmethod
    def generar_siguiente_correlativo() -> str:
        """Calcula el siguiente correlativo para la serie F001."""
        conteo = len(DB_FACTURAS) + 1
        return f"F001-{conteo:06d}"
