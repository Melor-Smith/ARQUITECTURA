"""Vista JSON de migraciones y Kardex (formato 12.1 impreso: incluye saldo final)."""

from __future__ import annotations

from src.adapters.inbound.http.esquemas import (
    CodigoDescripcion,
    ConciliacionSalida,
    DocumentoSoporteSalida,
    HomologacionSalida,
    KardexSalida,
    LoteSalida,
    MigracionSalida,
    MovimientoSalida,
    ProductoSalida,
    ResultadoFichaSalida,
    ResumenLoteSalida,
)
from src.domain.inventario import Kardex, MigracionLegado, MovimientoInventario
from src.domain.lotes import EstadoFichaLote, LoteMigracion


def _cd(enum) -> CodigoDescripcion:
    return CodigoDescripcion(codigo=enum.value, descripcion=enum.descripcion)


def movimiento_json(m: MovimientoInventario) -> MovimientoSalida:
    return MovimientoSalida(
        id=m.id, fecha=m.fecha, establecimiento=m.establecimiento, codigo_producto=m.producto.codigo,
        tipo_operacion=_cd(m.tipo_operacion),
        documento=DocumentoSoporteSalida(tipo=_cd(m.documento.tipo), serie=m.documento.serie,
                                         numero=m.documento.numero, fecha=m.documento.fecha),
        entrada=m.entrada, salida=m.salida, saldo=m.saldo, glosa=m.glosa,
    )


def lote_json(lote: LoteMigracion) -> LoteSalida:
    return LoteSalida(
        id_lote=lote.id,
        procesado_en=lote.procesado_en,
        resumen=ResumenLoteSalida(
            total=len(lote.resultados), migradas=lote.contar(EstadoFichaLote.MIGRADA),
            observadas=lote.contar(EstadoFichaLote.OBSERVADA), duplicadas=lote.contar(EstadoFichaLote.DUPLICADA),
            cuadra=lote.cuadra,
        ),
        conciliacion=[
            ConciliacionSalida(establecimiento=c.establecimiento, codigo_producto=c.codigo_producto,
                               saldo_inicial=c.saldo_inicial, entradas=c.entradas, salidas=c.salidas,
                               saldo_final=c.saldo_final, cuadra=c.cuadra)
            for c in lote.conciliacion
        ],
        resultados=[
            ResultadoFichaSalida(indice=r.indice, nro_documento=r.nro_documento, estado=r.estado.value,
                                 codigo=r.codigo, mensaje=r.mensaje,
                                 migracion=migracion_json(r.migracion) if r.migracion else None)
            for r in lote.resultados
        ],
    )


def migracion_json(m: MigracionLegado) -> MigracionSalida:
    h = m.homologacion
    return MigracionSalida(
        id_migracion=m.id, clave=m.identificador, nro_documento_legado=m.ficha.nro_documento,
        regla_documento=m.regla_documento, observaciones=list(m.observaciones),
        estado=m.estado, comprobante=m.comprobante,
        homologacion=HomologacionSalida(texto_legado=h.texto_legado, codigo_producto=h.codigo_producto,
                                        factor_conversion=h.factor_conversion),
        movimiento=movimiento_json(m.movimiento),
    )


def kardex_json(k: Kardex) -> KardexSalida:
    p = k.producto
    return KardexSalida(
        establecimiento=k.establecimiento,
        producto=ProductoSalida(codigo=p.codigo, descripcion=p.descripcion, unidad_medida=_cd(p.unidad),
                                unidad_medida_ple=_cd(p.unidad), tipo_existencia=_cd(p.tipo_existencia)),
        saldo_final=k.saldo,
        movimientos=[movimiento_json(m) for m in k.movimientos],
    )
