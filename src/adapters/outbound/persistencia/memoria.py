"""Adaptadores de persistencia en memoria (desarrollo y pruebas).

Implementan los puertos de ``src/application/puertos.py``. Cada instancia tiene su
propio estado: no hay variables globales, así que cada prueba arma un contenedor limpio.

Implementan los mismos puertos que ``sqlite.py`` (ADR 0011), el adaptador con datos
duraderos y transacciones reales; las pruebas de aceptación corren contra los dos.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

from src.application.errores import Conflicto
from src.application.puertos import RegistroIdempotencia
from src.domain.catalogos import TipoComprobante
from src.domain.comprobante import Comprobante
from src.domain.errores import CorrelativoInvalido
from src.domain.inventario import (
    Homologacion,
    Kardex,
    MigracionLegado,
    MovimientoInventario,
    Producto,
    normalizar_texto,
)
from src.domain.lotes import LoteMigracion
from src.domain.valores import CORRELATIVO_MAXIMO, Correlativo, Ruc, Serie


class UnidadDeTrabajoEnMemoria:
    """Serializa las transacciones con un ``RLock`` (reentrante para casos de uso anidados)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

    @contextmanager
    def transaccion(self) -> Iterator[None]:
        with self._lock:
            yield


class SecuenciaCorrelativosEnMemoria:
    """``ultimos`` permite continuar series ya usadas en otro sistema: {(ruc, tipo, serie): último número}."""

    def __init__(self, ultimos: dict[tuple[str, str, str], int] | None = None) -> None:
        self._lock = threading.Lock()
        self._ultimos: dict[tuple[str, str, str], int] = dict(ultimos or {})

    def siguiente(self, ruc: Ruc, tipo: TipoComprobante, serie: Serie) -> Correlativo:
        clave = (str(ruc), tipo.value, str(serie))
        with self._lock:
            siguiente = self._ultimos.get(clave, 0) + 1
            if siguiente > CORRELATIVO_MAXIMO:
                raise CorrelativoInvalido(
                    f"La serie {serie} del tipo {tipo.value} agotó sus {CORRELATIVO_MAXIMO:,} correlativos; "
                    "debe habilitarse una serie nueva.",
                    codigo="ERR-SUNAT-SERIE-AGOTADA",
                )
            self._ultimos[clave] = siguiente
        return Correlativo(siguiente)


class GeneradorIdentificadoresEnMemoria:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._contadores: dict[str, int] = {}

    def siguiente(self, prefijo: str) -> str:
        with self._lock:
            valor = self._contadores.get(prefijo, 0) + 1
            self._contadores[prefijo] = valor
        return f"{prefijo}-{valor:06d}"


class RepositorioComprobantesEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[tuple[TipoComprobante, str], Comprobante] = {}

    def agregar(self, comprobante: Comprobante) -> None:
        if comprobante.clave in self._datos:
            raise Conflicto(
                f"Ya existe el comprobante {comprobante.tipo.value}/{comprobante.serie_numero}.",
                codigo="ERR-COMPROBANTE-DUPLICADO",
            )
        self._datos[comprobante.clave] = comprobante

    def actualizar(self, comprobante: Comprobante) -> None:
        self._datos[comprobante.clave] = comprobante

    def obtener(self, tipo: TipoComprobante, serie_numero: str) -> Comprobante | None:
        return self._datos.get((tipo, serie_numero))

    def listar(self) -> Iterator[Comprobante]:
        return iter(list(self._datos.values()))

    def notas_de(self, referencia: Comprobante) -> list[Comprobante]:
        return [c for c in self._datos.values() if c.referencia is not None and c.referencia.clave == referencia.clave]


class RepositorioIdempotenciaEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, RegistroIdempotencia] = {}

    def obtener(self, clave: str) -> RegistroIdempotencia | None:
        return self._datos.get(clave)

    def guardar(self, clave: str, registro: RegistroIdempotencia) -> None:
        self._datos[clave] = registro


class RepositorioProductosEnMemoria:
    def __init__(self, productos: list[Producto], homologaciones: list[Homologacion]) -> None:
        self._productos = {p.codigo: p for p in productos}
        self._homologaciones = {h.clave: h for h in homologaciones}

    def obtener(self, codigo: str) -> Producto | None:
        return self._productos.get(codigo)

    def homologar(self, texto_legado: str) -> Homologacion | None:
        return self._homologaciones.get(normalizar_texto(texto_legado))


class RepositorioKardexEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[tuple[str, str], Kardex] = {}

    def obtener(self, establecimiento: str, producto: Producto) -> Kardex:
        clave = (establecimiento, producto.codigo)
        if clave not in self._datos:
            self._datos[clave] = Kardex(establecimiento, producto)
        return self._datos[clave]

    def guardar(self, kardex: Kardex) -> None:
        self._datos[(kardex.establecimiento, kardex.producto.codigo)] = kardex

    def movimientos(self) -> Iterator[MovimientoInventario]:
        for kardex in list(self._datos.values()):
            yield from kardex.movimientos


class RepositorioMigracionesEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, MigracionLegado] = {}

    def obtener(self, nro_documento: str) -> MigracionLegado | None:
        return self._datos.get(nro_documento.strip())

    def guardar(self, migracion: MigracionLegado) -> None:
        self._datos[migracion.identificador] = migracion


class RepositorioLotesEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, LoteMigracion] = {}

    def guardar(self, lote: LoteMigracion) -> None:
        self._datos[lote.id] = lote

    def obtener(self, id_lote: str) -> LoteMigracion | None:
        return self._datos.get(id_lote)
