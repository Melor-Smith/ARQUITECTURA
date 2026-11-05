"""Casos de uso de libros electrónicos del PLE."""

from __future__ import annotations

from src.application.puertos import RepositorioComprobantes, RepositorioKardex
from src.domain.libros import LibroElectronico, Periodo, inventario_121, registro_ventas_141
from src.domain.valores import Ruc


class GenerarRegistroVentas141:
    def __init__(self, *, ruc: Ruc, comprobantes: RepositorioComprobantes) -> None:
        self._ruc = ruc
        self._comprobantes = comprobantes

    def ejecutar(self, periodo: str) -> LibroElectronico:
        return registro_ventas_141(self._ruc, Periodo.parsear(periodo), self._comprobantes.listar())


class GenerarInventario121:
    def __init__(self, *, ruc: Ruc, kardex: RepositorioKardex) -> None:
        self._ruc = ruc
        self._kardex = kardex

    def ejecutar(self, periodo: str) -> LibroElectronico:
        return inventario_121(self._ruc, Periodo.parsear(periodo), self._kardex.movimientos())
