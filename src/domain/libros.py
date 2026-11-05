"""Libros electrónicos del PLE (RS 286-2009/SUNAT y modificatorias).

* Formato 14.1: Registro de Ventas e Ingresos.
* Formato 12.1: Registro del Inventario Permanente en Unidades Físicas.

Aquí viven las filas como datos tipados, con los valores que pide el PLE (por ejemplo, las
salidas del 12.1 en negativo). El layout del TXT (número, tipo, longitud y obligatoriedad de
cada campo) está en ``ple_estructura``, contrastado con el Excel oficial del Anexo 2.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from src.domain.catalogos import CatalogoExistencias, Moneda, TipoComprobante, TipoDocumentoIdentidad
from src.domain.comprobante import Comprobante
from src.domain.errores import ErrorDominio
from src.domain.inventario import MovimientoInventario
from src.domain.tributos import CERO, redondear
from src.domain.valores import Ruc

_PATRON_PERIODO = re.compile(r"^(\d{4})(0[1-9]|1[0-2])$")


@dataclass(frozen=True, slots=True, order=True)
class Periodo:
    anio: int
    mes: int

    @classmethod
    def parsear(cls, texto: str) -> Periodo:
        coincidencia = _PATRON_PERIODO.match(texto)
        if not coincidencia:
            raise ErrorDominio(f"El periodo '{texto}' debe tener el formato AAAAMM.", codigo="ERR-PLE-PERIODO")
        return cls(int(coincidencia.group(1)), int(coincidencia.group(2)))

    def contiene(self, fecha: dt.date) -> bool:
        return fecha.year == self.anio and fecha.month == self.mes

    @property
    def codigo_ple(self) -> str:
        """Campo 1 de ambos formatos: AAAAMM00."""
        return f"{self.anio:04d}{self.mes:02d}00"

    def __str__(self) -> str:
        return f"{self.anio:04d}{self.mes:02d}"


@dataclass(frozen=True, slots=True)
class LibroElectronico:
    identificador: str  # 140100 o 120100
    ruc: Ruc
    periodo: Periodo
    filas: tuple

    @property
    def nombre_archivo(self) -> str:
        """Hoja "Reglas de nombres de libros" del Anexo 2:

        ``LE`` + RUC + AAAA + MM + DD (``00``) + libro (6) + oportunidad CC (``00``)
        + O operaciones (``1`` empresa operativa) + I contenido (``1`` con información,
        ``0`` sin información) + M moneda (``1`` soles) + G generado por PLE (``1``).
        """
        contenido = "1" if self.filas else "0"
        return (f"LE{self.ruc}{self.periodo.codigo_ple}{self.identificador}00"
                f"{INDICADOR_EMPRESA_OPERATIVA}{contenido}{MONEDA_SOLES}{GENERADO_POR_PLE}.txt")


@dataclass(frozen=True, slots=True)
class FilaRegistroVentas141:
    """Una fila del formato 14.1. Los importes están en soles (moneda del libro)."""

    periodo: str  # 1
    cuo: str  # 2
    correlativo_asiento: str  # 3
    fecha_emision: dt.date  # 4
    fecha_vencimiento: dt.date | None  # 5
    tipo_comprobante: str  # 6 (tabla 10)
    serie: str  # 7
    numero: str  # 8
    numero_final: str  # 9 (solo para resúmenes de tickets)
    tipo_documento_cliente: str  # 10 (tabla 2)
    numero_documento_cliente: str  # 11
    nombre_cliente: str  # 12
    valor_exportacion: Decimal  # 13
    base_gravada: Decimal  # 14
    descuento_base_gravada: Decimal  # 15
    igv: Decimal  # 16
    descuento_igv: Decimal  # 17
    importe_exonerado: Decimal  # 18
    importe_inafecto: Decimal  # 19
    isc: Decimal  # 20
    base_ivap: Decimal  # 21
    ivap: Decimal  # 22
    icbper: Decimal  # 23
    otros_tributos: Decimal  # 24
    importe_total: Decimal  # 25
    moneda: str  # 26 (tabla 4)
    tipo_cambio: Decimal  # 27
    fecha_modificado: dt.date | None  # 28
    tipo_modificado: str  # 29
    serie_modificado: str  # 30
    numero_modificado: str  # 31
    contrato: str  # 32
    error_tipo_cambio: str  # 33
    indicador_medio_pago: str  # 34
    estado: str  # 35


@dataclass(frozen=True, slots=True)
class FilaInventario121:
    """Una fila del formato 12.1 (un movimiento de inventario)."""

    periodo: str  # 1
    cuo: str  # 2
    correlativo_asiento: str  # 3
    establecimiento: str  # 4
    catalogo: str  # 5 (tabla 13)
    tipo_existencia: str  # 6 (tabla 5)
    codigo_existencia: str  # 7
    catalogo_internacional: str  # 8 (tabla 13: UNSPSC/GTIN, obligatorio si el CPE lo consignó)
    codigo_internacional: str  # 9
    fecha_documento: dt.date  # 10
    tipo_documento: str  # 11 (tabla 10)
    serie_documento: str  # 12 ("0" si no existe)
    numero_documento: str  # 13 ("0" si no existe)
    tipo_operacion: str  # 14 (tabla 12)
    descripcion_existencia: str  # 15
    unidad_medida: str  # 16 (tabla 6, no UNECE)
    entrada: Decimal  # 17 (positivo o 0.00)
    salida: Decimal  # 18 (negativo o 0.00)
    estado: str  # 19
    saldo_final: Decimal  # no va en el TXT; lo usa la vista JSON del formato impreso


#: Estado de la anotación: 1 = la operación corresponde al periodo.
ESTADO_OPERACION_DEL_PERIODO = "1"
#: Posiciones 30, 32 y 33 del nombre del archivo.
INDICADOR_EMPRESA_OPERATIVA = "1"
MONEDA_SOLES = "1"
GENERADO_POR_PLE = "1"
#: Sin catálogo internacional: el sistema no emite códigos UNSPSC ni GTIN en el XML, así que
#: los campos 8 y 9 del 12.1 son opcionales y van vacíos.
SIN_CATALOGO_INTERNACIONAL = ""


def _ultimo_dia_del_mes_siguiente(periodo: Periodo) -> dt.date:
    anio, mes = (periodo.anio + 1, 1) if periodo.mes == 12 else (periodo.anio, periodo.mes + 1)
    return dt.date(anio, mes, calendar.monthrange(anio, mes)[1])


def registro_ventas_141(ruc: Ruc, periodo: Periodo, comprobantes: Iterable[Comprobante]) -> LibroElectronico:
    """Construye el 14.1. Excluye los comprobantes rechazados (no tienen validez tributaria);
    las notas de crédito se anotan en negativo."""
    del_periodo = sorted(
        (c for c in comprobantes if periodo.contiene(c.fecha_emision) and c.es_valido_tributariamente),
        key=lambda c: (c.fecha_emision, c.hora_emision, c.tipo.value, c.serie_numero),
    )
    filas = tuple(_fila_141(periodo, indice, c) for indice, c in enumerate(del_periodo, start=1))
    return LibroElectronico("140100", ruc, periodo, filas)


def _fila_141(periodo: Periodo, indice: int, c: Comprobante) -> FilaRegistroVentas141:
    signo = Decimal(-1) if c.tipo is TipoComprobante.NOTA_CREDITO else Decimal(1)
    tipo_cambio = c.tipo_cambio if c.moneda is Moneda.USD and c.tipo_cambio else Decimal("1")

    def en_soles(monto: Decimal) -> Decimal:
        convertido = redondear(monto * tipo_cambio)
        return convertido * signo if convertido else redondear(CERO)  # evita "-0.00"

    ref = c.referencia
    t = c.totales
    # Campo 5: el PLE solo acepta fechas hasta el último día del mes siguiente al periodo.
    # El vencimiento de un crédito más largo sigue en el XML (cac:PaymentTerms), no aquí.
    vencimiento = c.forma_pago.fecha_vencimiento if c.forma_pago else None
    if vencimiento and vencimiento > _ultimo_dia_del_mes_siguiente(periodo):
        vencimiento = None
    # Campos 10 y 11: en una boleta a cliente no identificado ("varios", tipo 0) el PLE
    # exige dejarlos vacíos; no acepta el valor 0.
    documento = c.cliente.documento
    anonimo = c.tipo is TipoComprobante.BOLETA and documento.tipo is TipoDocumentoIdentidad.NO_DOMICILIADO
    return FilaRegistroVentas141(
        periodo=periodo.codigo_ple,
        cuo=f"V{periodo}{indice:06d}",
        correlativo_asiento=f"M{indice}",
        fecha_emision=c.fecha_emision,
        fecha_vencimiento=vencimiento,
        tipo_comprobante=c.tipo.value,
        serie=str(c.numero.serie),
        numero=str(c.numero.correlativo),
        numero_final="",
        tipo_documento_cliente="" if anonimo else documento.tipo.value,
        numero_documento_cliente="" if anonimo else documento.numero,
        nombre_cliente=c.cliente.nombre,
        valor_exportacion=en_soles(t.exportacion),
        # Campo 14: valor de venta gravado SIN el ISC; el ISC se anota aparte en el campo 20,
        # de modo que 13 + 14 + 16 + 18 + 19 + 20 + 23 = 25 (importe total).
        base_gravada=en_soles(t.gravadas),
        descuento_base_gravada=CERO,
        igv=en_soles(t.igv),
        descuento_igv=CERO,
        importe_exonerado=en_soles(t.exoneradas),
        importe_inafecto=en_soles(t.inafectas),
        isc=en_soles(t.isc),
        base_ivap=CERO,
        ivap=CERO,
        icbper=en_soles(t.icbper),
        otros_tributos=CERO,
        importe_total=en_soles(t.importe_total),
        moneda=c.moneda.value,
        tipo_cambio=tipo_cambio,
        fecha_modificado=ref.fecha_emision if ref else None,
        tipo_modificado=ref.tipo.value if ref else "",
        serie_modificado=str(ref.numero.serie) if ref else "",
        numero_modificado=str(ref.numero.correlativo) if ref else "",
        contrato="",
        error_tipo_cambio="",
        indicador_medio_pago="",
        estado=ESTADO_OPERACION_DEL_PERIODO,
    )


def inventario_121(ruc: Ruc, periodo: Periodo, movimientos: Iterable[MovimientoInventario]) -> LibroElectronico:
    del_periodo = sorted(
        (m for m in movimientos if periodo.contiene(m.fecha)),
        key=lambda m: (m.establecimiento, m.producto.codigo, m.fecha, m.id),
    )
    filas = tuple(
        FilaInventario121(
            periodo=periodo.codigo_ple,
            cuo=f"I{periodo}{indice:06d}",
            correlativo_asiento=f"M{indice}",
            establecimiento=m.establecimiento,
            catalogo=CatalogoExistencias.OTROS.value,
            tipo_existencia=m.producto.tipo_existencia.value,
            codigo_existencia=m.producto.codigo,
            catalogo_internacional=SIN_CATALOGO_INTERNACIONAL,
            codigo_internacional=SIN_CATALOGO_INTERNACIONAL,
            fecha_documento=m.documento.fecha,
            tipo_documento=m.documento.tipo.value,
            serie_documento=m.documento.serie or "0",
            numero_documento=m.documento.numero or "0",
            tipo_operacion=m.tipo_operacion.value,
            descripcion_existencia=m.producto.descripcion,
            unidad_medida=m.producto.unidad.unidad_ple.value,
            entrada=m.entrada,
            salida=CERO - m.salida,  # campo 18: las salidas se anotan en negativo
            estado=ESTADO_OPERACION_DEL_PERIODO,
            saldo_final=m.saldo,
        )
        for indice, m in enumerate(del_periodo, start=1)
    )
    return LibroElectronico("120100", ruc, periodo, filas)
