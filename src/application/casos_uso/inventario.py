"""Casos de uso de inventario: migración de fichas del sistema antiguo y consulta de Kardex."""

from __future__ import annotations

import datetime as dt
import hashlib
from decimal import Decimal

from src.application.comandos import MigrarFichaLegadoCmd
from src.application.errores import Conflicto, RecursoNoEncontrado
from src.application.puertos import (
    GeneradorIdentificadores,
    Reloj,
    RepositorioKardex,
    RepositorioLotes,
    RepositorioMigraciones,
    RepositorioProductos,
    UnidadDeTrabajo,
)
from src.domain.catalogos import SentidoMovimiento, TipoDocumentoPLE, TipoOperacionInventario
from src.domain.errores import ErrorDominio
from src.domain.inventario import (
    DocumentoClasificado,
    EstadoMigracion,
    FichaLegado,
    Homologacion,
    Kardex,
    MigracionLegado,
    clasificar_documento_legado,
    parsear_fecha_legado,
)
from src.domain.lotes import ConciliacionProducto, EstadoFichaLote, LoteMigracion, ResultadoFicha
from src.domain.tributos import CERO


def clave_migracion(fecha: dt.date, cmd: MigrarFichaLegadoCmd, clasificado: DocumentoClasificado) -> str:
    """Identifica una ficha para detectar duplicados. Las fichas sin documento ("S/N") no tienen un
    número que las distinga, así que se identifican por el resumen de su contenido."""
    if clasificado.regla != "SIN_DOCUMENTO":
        return cmd.nro_documento.strip()
    contenido = f"{fecha}|{cmd.producto.strip().upper()}|{cmd.ingreso}|{cmd.salida}"
    return "SN-" + hashlib.sha256(contenido.encode()).hexdigest()[:12].upper()


def fecha_de(cmd: MigrarFichaLegadoCmd) -> dt.date:
    return cmd.fecha if isinstance(cmd.fecha, dt.date) else parsear_fecha_legado(cmd.fecha)


class MigrarFichaLegado:
    """Convierte una ficha informal en un movimiento del inventario permanente (formato 12.1).

    El ``nro_documento`` se clasifica por lo que realmente es (factura o boleta física, guía de
    remisión, comprobante electrónico o documento interno) y nunca se convierte en un número de
    comprobante SUNAT nuevo: la serie y el correlativo solo nacen cuando se emite el comprobante.
    """

    def __init__(self, *, uow: UnidadDeTrabajo, productos: RepositorioProductos, kardex: RepositorioKardex,
                 migraciones: RepositorioMigraciones, ids: GeneradorIdentificadores,
                 establecimiento_por_defecto: str) -> None:
        self._uow = uow
        self._productos = productos
        self._kardex = kardex
        self._migraciones = migraciones
        self._ids = ids
        self._establecimiento = establecimiento_por_defecto

    def ejecutar(self, cmd: MigrarFichaLegadoCmd) -> MigracionLegado:
        fecha = fecha_de(cmd)
        ficha = FichaLegado(fecha, cmd.ingreso, cmd.salida, cmd.producto.strip(), cmd.nro_documento.strip())
        clasificado = clasificar_documento_legado(ficha.nro_documento, fecha)
        clave = clave_migracion(fecha, cmd, clasificado)
        with self._uow.transaccion():
            existente = self._migraciones.obtener(clave)
            if existente is not None:
                raise Conflicto(
                    f"El documento legado '{ficha.nro_documento}' ya fue migrado ({existente.id}).",
                    codigo="ERR-LEGADO-DUPLICADO",
                )
            homologacion = self._homologar(cmd, ficha)
            producto = self._productos.obtener(homologacion.codigo_producto)
            if producto is None:
                raise ErrorDominio(f"El producto '{homologacion.codigo_producto}' no existe en el catálogo.",
                                   codigo="ERR-PRODUCTO-NO-EXISTE", campo="codigo_producto")

            es_salida = ficha.sentido is SentidoMovimiento.SALIDA
            # Lo que ocurrió en el negocio (una venta o una compra) no siempre es lo que se anota
            # en el 12.1: SUNAT exige comprobante o guía para las operaciones 01 a 06. Si la ficha
            # solo tiene un documento interno y no se indicó la operación, se anota como 99.
            es_venta = es_salida and cmd.tipo_operacion in (None, TipoOperacionInventario.VENTA)
            operacion = cmd.tipo_operacion or (TipoOperacionInventario.VENTA if es_salida
                                               else TipoOperacionInventario.COMPRA)
            observaciones = [clasificado.observacion] if clasificado.observacion else []
            if (cmd.tipo_operacion is None and operacion.exige_comprobante
                    and clasificado.documento.tipo is TipoDocumentoPLE.OTROS):
                observaciones.append(
                    f"Sustentada solo con documento interno: en el 12.1 se anota como operación 99 (Otros) y no "
                    f"{operacion.value} ({operacion.descripcion}), porque SUNAT exige comprobante o guía de remisión.")
                operacion = TipoOperacionInventario.OTROS
            kardex = self._kardex.obtener(cmd.establecimiento or self._establecimiento, producto)
            movimiento = kardex.registrar(
                id_movimiento=self._ids.siguiente("MOV"),
                fecha=ficha.fecha,
                tipo_operacion=operacion,
                sentido=ficha.sentido,
                cantidad=ficha.cantidad * homologacion.factor_conversion,
                documento=clasificado.documento,
                glosa=f"Migrado del sistema antiguo: {ficha.producto}",
            )
            if not es_venta:
                estado = EstadoMigracion.NO_REQUIERE_FACTURA
            elif clasificado.documento.tipo in (TipoDocumentoPLE.FACTURA, TipoDocumentoPLE.BOLETA):
                estado = EstadoMigracion.FACTURADA_EN_SISTEMA_ANTIGUO  # no se vuelve a facturar
            else:
                estado = EstadoMigracion.PENDIENTE_FACTURACION
            migracion = MigracionLegado(
                self._ids.siguiente("MIG"), ficha, homologacion, movimiento, estado,
                regla_documento=clasificado.regla,
                observaciones=tuple(observaciones),
                clave=clave,
            )
            self._kardex.guardar(kardex)
            self._migraciones.guardar(migracion)
        return migracion

    def _homologar(self, cmd: MigrarFichaLegadoCmd, ficha: FichaLegado) -> Homologacion:
        if cmd.codigo_producto:
            return Homologacion(ficha.producto, cmd.codigo_producto, cmd.factor_conversion or Decimal("1"))
        homologacion = self._productos.homologar(ficha.producto)
        if homologacion is None:
            raise ErrorDominio(
                f"La glosa '{ficha.producto}' no está en la tabla de homologación; envíe 'codigo_producto' "
                "y 'factor_conversion'.",
                codigo="ERR-LEGADO-NO-HOMOLOGADO", campo="producto",
            )
        return homologacion


class MigrarLoteLegado:
    """Migra un archivo completo de fichas sin detenerse ante la primera falla.

    1. Ordena las fichas por fecha, porque el Kardex exige orden cronológico y el sistema antiguo
       no lo garantizaba. Las fechas ilegibles van al final y quedan observadas.
    2. Cada ficha se migra con las mismas reglas que la migración individual. Las fallas de regla
       no detienen el lote: la ficha queda OBSERVADA con su código de error.
    3. Concilia por producto el saldo inicial + entradas − salidas contra el saldo final del Kardex.
    """

    def __init__(self, *, uow: UnidadDeTrabajo, migrar: MigrarFichaLegado, kardex: RepositorioKardex,
                 lotes: RepositorioLotes, ids: GeneradorIdentificadores, reloj: Reloj) -> None:
        self._uow = uow
        self._migrar = migrar
        self._kardex = kardex
        self._lotes = lotes
        self._ids = ids
        self._reloj = reloj

    def ejecutar(self, fichas: list[MigrarFichaLegadoCmd]) -> LoteMigracion:
        def orden(item: tuple[int, MigrarFichaLegadoCmd]) -> tuple[dt.date, int]:
            indice, cmd = item
            try:
                return fecha_de(cmd), indice
            except ErrorDominio:
                return dt.date.max, indice

        resultados: list[ResultadoFicha] = []
        with self._uow.transaccion():
            for indice, cmd in sorted(enumerate(fichas, start=1), key=orden):
                try:
                    migracion = self._migrar.ejecutar(cmd)
                    resultados.append(ResultadoFicha(indice, cmd.nro_documento, EstadoFichaLote.MIGRADA, migracion))
                except Conflicto as exc:
                    resultados.append(ResultadoFicha(indice, cmd.nro_documento, EstadoFichaLote.DUPLICADA,
                                                     codigo=exc.codigo, mensaje=exc.mensaje))
                except ErrorDominio as exc:
                    resultados.append(ResultadoFicha(indice, cmd.nro_documento, EstadoFichaLote.OBSERVADA,
                                                     codigo=exc.codigo, mensaje=exc.mensaje))
            lote = LoteMigracion(self._ids.siguiente("LOTE"), self._reloj.ahora(),
                                 tuple(sorted(resultados, key=lambda r: r.indice)), self._conciliar(resultados))
            self._lotes.guardar(lote)
        return lote

    def _conciliar(self, resultados: list[ResultadoFicha]) -> tuple[ConciliacionProducto, ...]:
        acumulado: dict[tuple[str, str], list] = {}
        for r in resultados:
            if r.migracion is None:
                continue
            m = r.migracion.movimiento
            clave = (m.establecimiento, m.producto.codigo)
            if clave not in acumulado:
                # saldo antes del primer movimiento del lote para este producto
                acumulado[clave] = [m.saldo - m.entrada + m.salida, CERO, CERO, m.producto]
            acumulado[clave][1] += m.entrada
            acumulado[clave][2] += m.salida
        return tuple(
            ConciliacionProducto(est, codigo, inicial, entradas, salidas,
                                 self._kardex.obtener(est, producto).saldo)
            for (est, codigo), (inicial, entradas, salidas, producto) in sorted(acumulado.items())
        )


class ConsultarLote:
    def __init__(self, *, lotes: RepositorioLotes) -> None:
        self._lotes = lotes

    def ejecutar(self, id_lote: str) -> LoteMigracion:
        lote = self._lotes.obtener(id_lote)
        if lote is None:
            raise RecursoNoEncontrado(f"No existe el lote '{id_lote}'.", codigo="ERR-LOTE-NO-ENCONTRADO")
        return lote


class ConsultarMigracion:
    def __init__(self, *, migraciones: RepositorioMigraciones) -> None:
        self._migraciones = migraciones

    def ejecutar(self, nro_documento: str) -> MigracionLegado:
        migracion = self._migraciones.obtener(nro_documento)
        if migracion is None:
            raise RecursoNoEncontrado(f"El documento legado '{nro_documento}' no ha sido migrado.",
                                      codigo="ERR-MIGRACION-NO-ENCONTRADA")
        return migracion


class ConsultarKardex:
    def __init__(self, *, productos: RepositorioProductos, kardex: RepositorioKardex,
                 establecimiento_por_defecto: str) -> None:
        self._productos = productos
        self._kardex = kardex
        self._establecimiento = establecimiento_por_defecto

    def ejecutar(self, codigo_producto: str, establecimiento: str | None = None) -> Kardex:
        producto = self._productos.obtener(codigo_producto)
        if producto is None:
            raise RecursoNoEncontrado(f"El producto '{codigo_producto}' no existe.",
                                      codigo="ERR-PRODUCTO-NO-ENCONTRADO")
        return self._kardex.obtener(establecimiento or self._establecimiento, producto)
