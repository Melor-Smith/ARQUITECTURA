"""Lote de migración del sistema antiguo: resultado por ficha y conciliación por producto.

La conciliación es una regla de negocio (saldo inicial + entradas − salidas = saldo final
del Kardex): por eso el lote es parte del dominio y no un detalle del caso de uso.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from src.domain.inventario import MigracionLegado


class EstadoFichaLote(str, Enum):
    MIGRADA = "MIGRADA"
    OBSERVADA = "OBSERVADA"  # no se migró: una regla la detuvo; se corrige y se reenvía
    DUPLICADA = "DUPLICADA"  # ya estaba migrada (reprocesar un lote es seguro)


@dataclass(frozen=True, slots=True)
class ResultadoFicha:
    indice: int  # posición en el archivo original (desde 1)
    nro_documento: str
    estado: EstadoFichaLote
    migracion: MigracionLegado | None = None
    codigo: str | None = None
    mensaje: str | None = None


@dataclass(frozen=True, slots=True)
class ConciliacionProducto:
    """Comprueba que el Kardex refleje exactamente las fichas migradas del lote."""

    establecimiento: str
    codigo_producto: str
    saldo_inicial: Decimal
    entradas: Decimal
    salidas: Decimal
    saldo_final: Decimal

    @property
    def cuadra(self) -> bool:
        return self.saldo_inicial + self.entradas - self.salidas == self.saldo_final


@dataclass(frozen=True, slots=True)
class LoteMigracion:
    id: str
    procesado_en: dt.datetime
    resultados: tuple[ResultadoFicha, ...]
    conciliacion: tuple[ConciliacionProducto, ...]

    def contar(self, estado: EstadoFichaLote) -> int:
        return sum(1 for r in self.resultados if r.estado is estado)

    @property
    def cuadra(self) -> bool:
        return all(c.cuadra for c in self.conciliacion)
