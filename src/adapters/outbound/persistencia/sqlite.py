"""Adaptadores de persistencia sobre SQLite (librería estándar, sin dependencias nuevas).

Implementan los mismos puertos que los adaptadores en memoria. Las pruebas de aceptación
corren contra ambos (``tests/conftest.py``), y eso es lo que demuestra que el hexágono
funciona: los casos de uso no saben dónde se guardan los datos.

Decisiones:

* **Transacciones reales.** ``BEGIN IMMEDIATE`` al abrir la transacción externa y
  ``SAVEPOINT`` en las anidadas. Así, en un lote de migración, una ficha que falla deshace
  solo su propio trabajo; las fichas buenas del mismo lote se conservan. Cualquier
  excepción hace ``ROLLBACK``.
* **Correlativo atómico** (ADR 0004): ``INSERT … ON CONFLICT DO UPDATE … RETURNING`` dentro
  de la transacción de emisión. Si la emisión falla, el número no se consume.
* **Unicidad garantizada por la base de datos:** clave primaria (tipo, serie_numero) en
  comprobantes. Un duplicado es ``Conflicto``, no un dato corrupto.
* **Agregados como documentos JSON** (``codec.py``) con columnas para las búsquedas.
  Leer siempre devuelve una copia nueva: modificar un objeto no cambia la base de datos
  hasta que se guarda, y un rollback no deja estado a medias en memoria.
"""

from __future__ import annotations

import itertools
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Any

from src.adapters.outbound.persistencia.codec import a_json, desde_json
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

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS correlativo (
    ruc TEXT NOT NULL, tipo TEXT NOT NULL, serie TEXT NOT NULL, ultimo INTEGER NOT NULL,
    PRIMARY KEY (ruc, tipo, serie));
CREATE TABLE IF NOT EXISTS identificador (prefijo TEXT PRIMARY KEY, ultimo INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS comprobante (
    tipo TEXT NOT NULL, serie_numero TEXT NOT NULL, referencia TEXT, documento TEXT NOT NULL,
    PRIMARY KEY (tipo, serie_numero));
CREATE INDEX IF NOT EXISTS comprobante_referencia ON comprobante (referencia);
CREATE TABLE IF NOT EXISTS idempotencia (
    clave TEXT PRIMARY KEY, huella TEXT NOT NULL, tipo TEXT NOT NULL, serie_numero TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS producto (codigo TEXT PRIMARY KEY, documento TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS homologacion (clave TEXT PRIMARY KEY, documento TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS kardex (
    establecimiento TEXT NOT NULL, codigo_producto TEXT NOT NULL, documento TEXT NOT NULL,
    PRIMARY KEY (establecimiento, codigo_producto));
CREATE TABLE IF NOT EXISTS migracion (identificador TEXT PRIMARY KEY, documento TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lote (id TEXT PRIMARY KEY, documento TEXT NOT NULL);
"""


class BaseDatosSqlite:
    """Una conexión compartida, protegida por un ``RLock``: SQLite admite un solo escritor."""

    def __init__(self, ruta: Path | str) -> None:
        if str(ruta) != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: las transacciones las abre y cierra esta clase, explícitamente.
        self._conexion = sqlite3.connect(str(ruta), isolation_level=None, check_same_thread=False)
        self._conexion.execute("PRAGMA foreign_keys = ON")
        self._conexion.execute("PRAGMA busy_timeout = 5000")
        if str(ruta) != ":memory:":
            self._conexion.execute("PRAGMA journal_mode = WAL")
        self._lock = threading.RLock()
        self._profundidad = 0
        self._puntos = itertools.count(1)
        with self._lock:
            self._conexion.executescript(_ESQUEMA)

    @contextmanager
    def transaccion(self) -> Iterator[None]:
        confirmar: tuple[str, ...]
        deshacer: tuple[str, ...]
        with self._lock:
            if self._profundidad == 0:
                inicio, confirmar, deshacer = "BEGIN IMMEDIATE", ("COMMIT",), ("ROLLBACK",)
            else:
                punto = f"sp{next(self._puntos)}"
                inicio, confirmar, deshacer = f"SAVEPOINT {punto}", (f"RELEASE {punto}",), (
                    f"ROLLBACK TO {punto}", f"RELEASE {punto}")
            self._conexion.execute(inicio)
            self._profundidad += 1
            try:
                yield
            except BaseException:
                self._profundidad -= 1
                for sentencia in deshacer:  # nunca executescript: haría un COMMIT implícito
                    self._conexion.execute(sentencia)
                raise
            self._profundidad -= 1
            for sentencia in confirmar:
                self._conexion.execute(sentencia)

    def uno(self, sql: str, parametros: tuple[Any, ...] = ()) -> tuple[Any, ...] | None:
        with self._lock:
            fila: tuple[Any, ...] | None = self._conexion.execute(sql, parametros).fetchone()
            return fila

    def todos(self, sql: str, parametros: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._lock:
            return self._conexion.execute(sql, parametros).fetchall()

    def ejecutar(self, sql: str, parametros: tuple[Any, ...] = ()) -> None:
        with self._lock, self.transaccion():
            self._conexion.execute(sql, parametros)

    def cerrar(self) -> None:
        with self._lock:
            self._conexion.close()


class UnidadDeTrabajoSqlite:
    def __init__(self, bd: BaseDatosSqlite) -> None:
        self._bd = bd

    def transaccion(self) -> AbstractContextManager[None]:
        return self._bd.transaccion()


class SecuenciaCorrelativosSqlite:
    def __init__(self, bd: BaseDatosSqlite, ultimos: dict[tuple[str, str, str], int] | None = None) -> None:
        self._bd = bd
        for (ruc, tipo, serie), ultimo in (ultimos or {}).items():
            # Solo se usa para continuar una serie que viene de otro sistema; nunca retrocede.
            bd.ejecutar("INSERT INTO correlativo VALUES (?, ?, ?, ?) "
                        "ON CONFLICT DO UPDATE SET ultimo = MAX(ultimo, excluded.ultimo)", (ruc, tipo, serie, ultimo))

    def siguiente(self, ruc: Ruc, tipo: TipoComprobante, serie: Serie) -> Correlativo:
        with self._bd.transaccion():
            fila = self._bd.uno(
                "INSERT INTO correlativo VALUES (?, ?, ?, 1) "
                "ON CONFLICT DO UPDATE SET ultimo = ultimo + 1 RETURNING ultimo",
                (str(ruc), tipo.value, str(serie)),
            )
            assert fila is not None
            if fila[0] > CORRELATIVO_MAXIMO:
                raise CorrelativoInvalido(
                    f"La serie {serie} del tipo {tipo.value} agotó sus {CORRELATIVO_MAXIMO:,} correlativos; "
                    "debe habilitarse una serie nueva.",
                    codigo="ERR-SUNAT-SERIE-AGOTADA",
                )
        return Correlativo(fila[0])


class GeneradorIdentificadoresSqlite:
    def __init__(self, bd: BaseDatosSqlite) -> None:
        self._bd = bd

    def siguiente(self, prefijo: str) -> str:
        with self._bd.transaccion():
            fila = self._bd.uno("INSERT INTO identificador VALUES (?, 1) "
                                "ON CONFLICT DO UPDATE SET ultimo = ultimo + 1 RETURNING ultimo", (prefijo,))
        assert fila is not None
        return f"{prefijo}-{fila[0]:06d}"


class RepositorioComprobantesSqlite:
    def __init__(self, bd: BaseDatosSqlite) -> None:
        self._bd = bd

    @staticmethod
    def _referencia(c: Comprobante) -> str | None:
        return f"{c.referencia.tipo.value}/{c.referencia.serie_numero}" if c.referencia else None

    def agregar(self, comprobante: Comprobante) -> None:
        try:
            self._bd.ejecutar("INSERT INTO comprobante VALUES (?, ?, ?, ?)",
                              (comprobante.tipo.value, comprobante.serie_numero, self._referencia(comprobante),
                               a_json(comprobante)))
        except sqlite3.IntegrityError as error:
            raise Conflicto(f"Ya existe el comprobante {comprobante.tipo.value}/{comprobante.serie_numero}.",
                            codigo="ERR-COMPROBANTE-DUPLICADO") from error

    def actualizar(self, comprobante: Comprobante) -> None:
        self._bd.ejecutar("UPDATE comprobante SET documento = ? WHERE tipo = ? AND serie_numero = ?",
                          (a_json(comprobante), comprobante.tipo.value, comprobante.serie_numero))

    def obtener(self, tipo: TipoComprobante, serie_numero: str) -> Comprobante | None:
        fila = self._bd.uno("SELECT documento FROM comprobante WHERE tipo = ? AND serie_numero = ?",
                            (tipo.value, serie_numero))
        return desde_json(Comprobante, fila[0]) if fila else None

    def listar(self) -> Iterator[Comprobante]:
        filas = self._bd.todos("SELECT documento FROM comprobante ORDER BY rowid")
        return iter([desde_json(Comprobante, f[0]) for f in filas])

    def notas_de(self, referencia: Comprobante) -> list[Comprobante]:
        filas = self._bd.todos("SELECT documento FROM comprobante WHERE referencia = ? ORDER BY rowid",
                               (f"{referencia.tipo.value}/{referencia.serie_numero}",))
        return [desde_json(Comprobante, f[0]) for f in filas]


class RepositorioIdempotenciaSqlite:
    def __init__(self, bd: BaseDatosSqlite) -> None:
        self._bd = bd

    def obtener(self, clave: str) -> RegistroIdempotencia | None:
        fila = self._bd.uno("SELECT huella, tipo, serie_numero FROM idempotencia WHERE clave = ?", (clave,))
        return RegistroIdempotencia(fila[0], TipoComprobante(fila[1]), fila[2]) if fila else None

    def guardar(self, clave: str, registro: RegistroIdempotencia) -> None:
        self._bd.ejecutar("INSERT OR REPLACE INTO idempotencia VALUES (?, ?, ?, ?)",
                          (clave, registro.huella, registro.tipo.value, registro.serie_numero))


class RepositorioProductosSqlite:
    """Catálogo de productos y tabla de homologación. Las semillas no pisan lo ya guardado."""

    def __init__(self, bd: BaseDatosSqlite, productos: list[Producto], homologaciones: list[Homologacion]) -> None:
        self._bd = bd
        with bd.transaccion():
            for p in productos:
                bd.ejecutar("INSERT OR IGNORE INTO producto VALUES (?, ?)", (p.codigo, a_json(p)))
            for h in homologaciones:
                bd.ejecutar("INSERT OR IGNORE INTO homologacion VALUES (?, ?)", (h.clave, a_json(h)))

    def obtener(self, codigo: str) -> Producto | None:
        fila = self._bd.uno("SELECT documento FROM producto WHERE codigo = ?", (codigo,))
        return desde_json(Producto, fila[0]) if fila else None

    def homologar(self, texto_legado: str) -> Homologacion | None:
        fila = self._bd.uno("SELECT documento FROM homologacion WHERE clave = ?", (normalizar_texto(texto_legado),))
        return desde_json(Homologacion, fila[0]) if fila else None


class RepositorioKardexSqlite:
    def __init__(self, bd: BaseDatosSqlite) -> None:
        self._bd = bd

    def obtener(self, establecimiento: str, producto: Producto) -> Kardex:
        fila = self._bd.uno("SELECT documento FROM kardex WHERE establecimiento = ? AND codigo_producto = ?",
                            (establecimiento, producto.codigo))
        return desde_json(Kardex, fila[0]) if fila else Kardex(establecimiento, producto)

    def guardar(self, kardex: Kardex) -> None:
        self._bd.ejecutar("INSERT OR REPLACE INTO kardex VALUES (?, ?, ?)",
                          (kardex.establecimiento, kardex.producto.codigo, a_json(kardex)))

    def movimientos(self) -> Iterator[MovimientoInventario]:
        for (documento,) in self._bd.todos("SELECT documento FROM kardex ORDER BY rowid"):
            yield from desde_json(Kardex, documento).movimientos

    def vacio(self) -> bool:
        return self._bd.uno("SELECT 1 FROM kardex LIMIT 1") is None


class RepositorioMigracionesSqlite:
    def __init__(self, bd: BaseDatosSqlite) -> None:
        self._bd = bd

    def obtener(self, nro_documento: str) -> MigracionLegado | None:
        fila = self._bd.uno("SELECT documento FROM migracion WHERE identificador = ?", (nro_documento.strip(),))
        return desde_json(MigracionLegado, fila[0]) if fila else None

    def guardar(self, migracion: MigracionLegado) -> None:
        self._bd.ejecutar("INSERT OR REPLACE INTO migracion VALUES (?, ?)",
                          (migracion.identificador, a_json(migracion)))


class RepositorioLotesSqlite:
    def __init__(self, bd: BaseDatosSqlite) -> None:
        self._bd = bd

    def guardar(self, lote: LoteMigracion) -> None:
        self._bd.ejecutar("INSERT OR REPLACE INTO lote VALUES (?, ?)", (lote.id, a_json(lote)))

    def obtener(self, id_lote: str) -> LoteMigracion | None:
        fila = self._bd.uno("SELECT documento FROM lote WHERE id = ?", (id_lote,))
        return desde_json(LoteMigracion, fila[0]) if fila else None
