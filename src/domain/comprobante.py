"""Agregado ``Comprobante``: factura (01), boleta (03), nota de crédito (07) y nota de débito (08).

El ciclo de vida es:

1. ``Linea.calcular`` calcula los tributos de cada línea con ``Decimal``.
2. ``BorradorComprobante.preparar`` valida las reglas cruzadas y totaliza. Todavía no tiene número.
3. ``BorradorComprobante.numerar`` asigna el correlativo que reservó el servidor.
4. ``Comprobante`` registra la firma y luego el CDR de la OSE; su estado sale del CDR,
   nunca de una constante.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from src.domain.catalogos import (
    AfectacionIGV,
    Moneda,
    MotivoNotaCredito,
    MotivoNotaDebito,
    TipoComprobante,
    TipoOperacionSunat,
    UnidadMedida,
)
from src.domain.errores import (
    ConflictoDominio,
    ReglaComprobanteIncumplida,
    ReglaTributariaIncumplida,
    UnidadMedidaInvalida,
)
from src.domain.letras import importe_en_letras
from src.domain.pagos import FormaPago, FormaPagoInvalida
from src.domain.tributos import CERO, TASA_IGV, ConfiguracionISC, redondear, tasa_icbper
from src.domain.valores import Correlativo, DocumentoIdentidad, NumeroComprobante, Ruc, Serie

#: Boletas por encima de este importe (en soles) exigen identificar al adquiriente.
LIMITE_BOLETA_SIN_IDENTIFICAR = Decimal("700.00")


@dataclass(frozen=True, slots=True)
class Emisor:
    """Datos del emisor. Vienen de la configuración del servidor, nunca del cliente HTTP."""

    ruc: Ruc
    razon_social: str
    nombre_comercial: str
    direccion: str
    ubigeo: str
    codigo_establecimiento: str = "0000"


@dataclass(frozen=True, slots=True)
class Cliente:
    documento: DocumentoIdentidad
    nombre: str
    direccion: str | None = None

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ReglaComprobanteIncumplida("El nombre o razón social del cliente es obligatorio.",
                                             campo="cliente.nombre")


@dataclass(frozen=True, slots=True)
class Linea:
    """Línea de detalle con sus tributos ya calculados por el dominio."""

    numero: int
    codigo_producto: str | None
    descripcion: str
    unidad: UnidadMedida
    cantidad: Decimal
    valor_unitario: Decimal
    afectacion: AfectacionIGV
    isc: ConfiguracionISC | None
    aplica_icbper: bool
    valor_venta: Decimal
    base_isc: Decimal
    monto_isc: Decimal
    base_igv: Decimal
    monto_igv: Decimal
    tasa_icbper: Decimal
    monto_icbper: Decimal

    @classmethod
    def calcular(
        cls,
        *,
        numero: int,
        descripcion: str,
        unidad: UnidadMedida,
        cantidad: Decimal,
        valor_unitario: Decimal,
        afectacion: AfectacionIGV,
        fecha_emision: dt.date,
        codigo_producto: str | None = None,
        isc: ConfiguracionISC | None = None,
        aplica_icbper: bool = False,
    ) -> Linea:
        campo = f"lineas[{numero - 1}]"
        if cantidad <= CERO:
            raise ReglaComprobanteIncumplida("La cantidad debe ser mayor a 0.", campo=f"{campo}.cantidad")
        if valor_unitario <= CERO:
            raise ReglaTributariaIncumplida(
                "El valor unitario debe ser mayor a 0: las operaciones gratuitas (afectaciones 11-17, 21, "
                "31-37) no están soportadas en esta versión.",
                campo=f"{campo}.valor_unitario",
            )
        if not descripcion.strip():
            raise ReglaComprobanteIncumplida("La descripción es obligatoria.", campo=f"{campo}.descripcion")
        if isc is not None and afectacion is AfectacionIGV.EXPORTACION:
            raise ReglaTributariaIncumplida("La exportación no está afecta al ISC.", campo=f"{campo}.isc")
        if aplica_icbper and unidad is not UnidadMedida.UNIDAD:
            raise UnidadMedidaInvalida(
                "El ICBPER se liquida por bolsa: la unidad de medida debe ser NIU.", campo=f"{campo}.unidad_medida"
            )

        cero = redondear(CERO)  # "0.00": los importes UBL van siempre con 2 decimales
        valor_venta = redondear(cantidad * valor_unitario)
        base_isc, monto_isc = isc.calcular(cantidad, valor_venta) if isc else (cero, cero)
        if afectacion.es_gravada:
            base_igv = valor_venta + monto_isc
            monto_igv = redondear(base_igv * TASA_IGV)
        else:
            base_igv, monto_igv = valor_venta, cero
        tasa_bolsa = tasa_icbper(fecha_emision) if aplica_icbper else CERO
        monto_icbper = redondear(cantidad * tasa_bolsa)

        return cls(
            numero=numero,
            codigo_producto=codigo_producto,
            descripcion=descripcion.strip(),
            unidad=unidad,
            cantidad=cantidad,
            valor_unitario=valor_unitario,
            afectacion=afectacion,
            isc=isc,
            aplica_icbper=aplica_icbper,
            valor_venta=valor_venta,
            base_isc=base_isc,
            monto_isc=monto_isc,
            base_igv=base_igv,
            monto_igv=monto_igv,
            tasa_icbper=tasa_bolsa,
            monto_icbper=monto_icbper,
        )

    @property
    def total_tributos(self) -> Decimal:
        return self.monto_isc + self.monto_igv + self.monto_icbper

    @property
    def precio_unitario(self) -> Decimal:
        """Precio unitario con IGV e ISC (``cac:PricingReference``, tipo de precio 01)."""
        return redondear((self.valor_venta + self.monto_isc + self.monto_igv) / self.cantidad)


@dataclass(frozen=True, slots=True)
class Totales:
    gravadas: Decimal
    exoneradas: Decimal
    inafectas: Decimal
    exportacion: Decimal
    base_isc: Decimal
    isc: Decimal
    igv: Decimal
    icbper: Decimal
    valor_venta: Decimal
    total_impuestos: Decimal
    importe_total: Decimal

    @classmethod
    def de_lineas(cls, lineas: tuple[Linea, ...]) -> Totales:
        def suma(valores) -> Decimal:
            return redondear(sum(valores, CERO))

        def por_afectacion(afectacion: AfectacionIGV) -> Decimal:
            return suma(ln.valor_venta for ln in lineas if ln.afectacion is afectacion)

        isc = suma(ln.monto_isc for ln in lineas)
        igv = suma(ln.monto_igv for ln in lineas)
        icbper = suma(ln.monto_icbper for ln in lineas)
        valor_venta = suma(ln.valor_venta for ln in lineas)
        total_impuestos = isc + igv + icbper
        return cls(
            gravadas=por_afectacion(AfectacionIGV.GRAVADO_ONEROSA),
            exoneradas=por_afectacion(AfectacionIGV.EXONERADO_ONEROSA),
            inafectas=por_afectacion(AfectacionIGV.INAFECTO_ONEROSA),
            exportacion=por_afectacion(AfectacionIGV.EXPORTACION),
            base_isc=suma(ln.base_isc for ln in lineas),
            isc=isc,
            igv=igv,
            icbper=icbper,
            valor_venta=valor_venta,
            total_impuestos=total_impuestos,
            importe_total=valor_venta + total_impuestos,
        )


class EstadoComprobante(str, Enum):
    REGISTRADO = "REGISTRADO"  # validado, numerado y firmado; aún sin respuesta de la OSE
    PENDIENTE_ENVIO = "PENDIENTE_ENVIO"  # la OSE no respondió; se reintentará
    ACEPTADO = "ACEPTADO"
    ACEPTADO_CON_OBSERVACIONES = "ACEPTADO_CON_OBSERVACIONES"
    RECHAZADO = "RECHAZADO"


@dataclass(frozen=True, slots=True)
class Cdr:
    """Constancia de recepción devuelta por la OSE/SUNAT."""

    codigo: str
    descripcion: str
    fecha_recepcion: dt.datetime
    observaciones: tuple[str, ...] = ()

    @property
    def estado_resultante(self) -> EstadoComprobante:
        codigo = int(self.codigo)
        if codigo == 0:
            return (EstadoComprobante.ACEPTADO_CON_OBSERVACIONES if self.observaciones
                    else EstadoComprobante.ACEPTADO)
        if 2000 <= codigo < 4000:
            return EstadoComprobante.RECHAZADO
        if codigo >= 4000:
            return EstadoComprobante.ACEPTADO_CON_OBSERVACIONES
        raise ReglaComprobanteIncumplida(
            f"El código {self.codigo} es una excepción: el comprobante no fue procesado y no hay CDR."
        )


Motivo = MotivoNotaCredito | MotivoNotaDebito


@dataclass(eq=False)
class Comprobante:
    tipo: TipoComprobante
    numero: NumeroComprobante
    fecha_emision: dt.date
    hora_emision: dt.time
    moneda: Moneda
    tipo_cambio: Decimal | None
    emisor: Emisor
    cliente: Cliente
    lineas: tuple[Linea, ...]
    totales: Totales
    documentos_legado: tuple[str, ...] = ()
    referencia: Comprobante | None = None
    motivo: Motivo | None = None
    sustento: str | None = None
    forma_pago: FormaPago | None = None  # obligatoria en facturas (RS 193-2020)
    estado: EstadoComprobante = EstadoComprobante.REGISTRADO
    xml_firmado: bytes | None = field(default=None, repr=False)
    hash_cpe: str | None = None
    cdr: Cdr | None = None
    intentos_envio: int = 0

    # --- identidad -------------------------------------------------------------------
    @property
    def serie_numero(self) -> str:
        return str(self.numero)

    @property
    def clave(self) -> tuple[TipoComprobante, str]:
        return self.tipo, self.serie_numero

    @property
    def nombre_archivo(self) -> str:
        """Nombre SUNAT del archivo: RUC-TIPO-SERIE-NUMERO."""
        return f"{self.emisor.ruc}-{self.tipo.value}-{self.serie_numero}"

    @property
    def tipo_operacion(self) -> TipoOperacionSunat:
        if all(ln.afectacion is AfectacionIGV.EXPORTACION for ln in self.lineas):
            return TipoOperacionSunat.EXPORTACION_BIENES
        return TipoOperacionSunat.VENTA_INTERNA

    @property
    def es_valido_tributariamente(self) -> bool:
        return self.estado is not EstadoComprobante.RECHAZADO

    @property
    def monto_en_letras(self) -> str:
        """Leyenda 1000 (Catálogo 52)."""
        return importe_en_letras(self.totales.importe_total, self.moneda)

    # --- comportamiento ----------------------------------------------------------------
    def registrar_firma(self, xml_firmado: bytes, hash_cpe: str) -> None:
        if self.xml_firmado is not None:
            raise ConflictoDominio(f"El comprobante {self.serie_numero} ya está firmado.")
        self.xml_firmado = xml_firmado
        self.hash_cpe = hash_cpe

    def asegurar_envio_posible(self) -> None:
        if self.xml_firmado is None:
            raise ConflictoDominio(f"El comprobante {self.serie_numero} no está firmado.")
        if self.estado not in (EstadoComprobante.REGISTRADO, EstadoComprobante.PENDIENTE_ENVIO):
            raise ConflictoDominio(
                f"El comprobante {self.serie_numero} ya tiene CDR (estado {self.estado.value}); no se reenvía.",
                codigo="ERR-COMPROBANTE-YA-PROCESADO",
            )

    def registrar_envio_fallido(self) -> None:
        self.asegurar_envio_posible()
        self.intentos_envio += 1
        self.estado = EstadoComprobante.PENDIENTE_ENVIO

    def registrar_cdr(self, cdr: Cdr) -> None:
        self.asegurar_envio_posible()
        self.intentos_envio += 1
        self.estado = cdr.estado_resultante
        self.cdr = cdr


@dataclass(frozen=True, slots=True)
class BorradorComprobante:
    """Comprobante validado y totalizado, a la espera del correlativo que asigna el servidor."""

    tipo: TipoComprobante
    serie: Serie
    fecha_emision: dt.date
    hora_emision: dt.time
    moneda: Moneda
    tipo_cambio: Decimal | None
    emisor: Emisor
    cliente: Cliente
    lineas: tuple[Linea, ...]
    totales: Totales
    documentos_legado: tuple[str, ...]
    referencia: Comprobante | None
    motivo: Motivo | None
    sustento: str | None
    forma_pago: FormaPago | None

    @classmethod
    def preparar(
        cls,
        *,
        tipo: TipoComprobante,
        serie: Serie,
        fecha_emision: dt.date,
        hora_emision: dt.time,
        hoy: dt.date,
        plazo_dias: int,
        moneda: Moneda,
        tipo_cambio: Decimal | None,
        emisor: Emisor,
        cliente: Cliente,
        lineas: tuple[Linea, ...],
        documentos_legado: tuple[str, ...] = (),
        referencia: Comprobante | None = None,
        motivo: Motivo | None = None,
        sustento: str | None = None,
        total_notas_credito_previas: Decimal = CERO,
        forma_pago: FormaPago | None = None,
    ) -> BorradorComprobante:
        if not lineas:
            raise ReglaComprobanteIncumplida("El comprobante debe tener al menos una línea.", campo="lineas")
        if tipo is TipoComprobante.FACTURA and forma_pago is None:
            forma_pago = FormaPago.contado()
        totales = Totales.de_lineas(lineas)
        borrador = cls(
            tipo=tipo, serie=serie, fecha_emision=fecha_emision, hora_emision=hora_emision,
            moneda=moneda, tipo_cambio=tipo_cambio, emisor=emisor, cliente=cliente, lineas=lineas,
            totales=totales, documentos_legado=documentos_legado, referencia=referencia,
            motivo=motivo, sustento=sustento.strip() if sustento else None, forma_pago=forma_pago,
        )
        borrador._validar_fecha(hoy, plazo_dias)
        borrador._validar_moneda()
        borrador._validar_forma_pago()
        if tipo.es_nota:
            borrador._validar_nota(total_notas_credito_previas)
        else:
            borrador._validar_venta()
        return borrador

    def numerar(self, correlativo: Correlativo) -> Comprobante:
        return Comprobante(
            tipo=self.tipo,
            numero=NumeroComprobante(self.serie, correlativo),
            fecha_emision=self.fecha_emision,
            hora_emision=self.hora_emision,
            moneda=self.moneda,
            tipo_cambio=self.tipo_cambio,
            emisor=self.emisor,
            cliente=self.cliente,
            lineas=self.lineas,
            totales=self.totales,
            documentos_legado=self.documentos_legado,
            referencia=self.referencia,
            motivo=self.motivo,
            sustento=self.sustento,
            forma_pago=self.forma_pago,
        )

    @property
    def importe_total_en_soles(self) -> Decimal:
        if self.moneda is Moneda.PEN:
            return self.totales.importe_total
        return redondear(self.totales.importe_total * (self.tipo_cambio or CERO))

    # --- reglas ------------------------------------------------------------------------
    def _validar_fecha(self, hoy: dt.date, plazo_dias: int) -> None:
        if self.fecha_emision > hoy:
            raise ReglaComprobanteIncumplida("La fecha de emisión no puede ser futura.", campo="fecha_emision",
                                             codigo="ERR-SUNAT-FECHA")
        if (hoy - self.fecha_emision).days > plazo_dias:
            raise ReglaComprobanteIncumplida(
                f"La fecha de emisión excede el plazo de envío de {plazo_dias} días calendario.",
                campo="fecha_emision", codigo="ERR-SUNAT-FECHA",
            )

    def _validar_moneda(self) -> None:
        if self.moneda is Moneda.USD and (self.tipo_cambio is None or self.tipo_cambio <= CERO):
            raise ReglaComprobanteIncumplida(
                "Las operaciones en USD requieren 'tipo_cambio' mayor a 0 (se usa en el registro de ventas 14.1).",
                campo="tipo_cambio",
            )
        if self.moneda is Moneda.PEN and self.tipo_cambio is not None:
            raise ReglaComprobanteIncumplida("Las operaciones en PEN no llevan 'tipo_cambio'.", campo="tipo_cambio")

    def _validar_forma_pago(self) -> None:
        if self.forma_pago is None:
            return
        if self.tipo is not TipoComprobante.FACTURA:
            raise FormaPagoInvalida("La forma de pago (RS 193-2020) solo se informa en facturas.",
                                    campo="forma_pago")
        self.forma_pago.validar(importe_total=self.totales.importe_total, fecha_emision=self.fecha_emision)

    def _validar_venta(self) -> None:
        if self.referencia is not None or self.motivo is not None:
            raise ReglaComprobanteIncumplida("Solo las notas de crédito o débito llevan referencia y motivo.")
        if len(set(self.documentos_legado)) != len(self.documentos_legado):
            raise ReglaComprobanteIncumplida("Hay documentos legado repetidos.", campo="documentos_legado")

        if self.tipo is TipoComprobante.FACTURA:
            if self.serie.letra != "F":
                raise ReglaComprobanteIncumplida(
                    f"Una factura (01) debe usar una serie que empiece con F; se recibió '{self.serie}'.",
                    campo="serie", codigo="ERR-SUNAT-SERIE",
                )
            exportacion = all(ln.afectacion is AfectacionIGV.EXPORTACION for ln in self.lineas)
            if not self.cliente.documento.es_ruc and not exportacion:
                raise ReglaComprobanteIncumplida(
                    "Una factura (01) requiere que el cliente se identifique con RUC (Catálogo 06, tipo 6), "
                    "salvo en exportaciones.",
                    campo="cliente.tipo_documento", codigo="ERR-SUNAT-RUC",
                )
        else:  # BOLETA
            if self.serie.letra != "B":
                raise ReglaComprobanteIncumplida(
                    f"Una boleta (03) debe usar una serie que empiece con B; se recibió '{self.serie}'.",
                    campo="serie", codigo="ERR-SUNAT-SERIE",
                )
            if self.cliente.documento.es_anonimo and self.importe_total_en_soles > LIMITE_BOLETA_SIN_IDENTIFICAR:
                raise ReglaComprobanteIncumplida(
                    f"Las boletas mayores a S/ {LIMITE_BOLETA_SIN_IDENTIFICAR} deben identificar al cliente "
                    "con DNI, carnet de extranjería, pasaporte o RUC.",
                    campo="cliente.tipo_documento",
                )

    def _validar_nota(self, total_notas_credito_previas: Decimal) -> None:
        ref = self.referencia
        if ref is None or self.motivo is None or not self.sustento:
            raise ReglaComprobanteIncumplida(
                "Una nota de crédito o débito requiere comprobante de referencia, motivo y sustento."
            )
        if self.documentos_legado:
            raise ReglaComprobanteIncumplida("Las notas no referencian documentos legado.", campo="documentos_legado")
        if ref.tipo not in (TipoComprobante.FACTURA, TipoComprobante.BOLETA):
            raise ReglaComprobanteIncumplida("Una nota solo puede modificar una factura o una boleta.",
                                             campo="referencia")
        if not ref.es_valido_tributariamente:
            raise ReglaComprobanteIncumplida(
                f"El comprobante {ref.serie_numero} fue rechazado: no puede modificarse con una nota.",
                campo="referencia",
            )
        if self.serie.letra != ref.numero.serie.letra:
            raise ReglaComprobanteIncumplida(
                f"La serie de la nota debe empezar con '{ref.numero.serie.letra}', igual que el comprobante "
                f"que modifica ({ref.serie_numero}).",
                campo="serie", codigo="ERR-SUNAT-SERIE",
            )
        if self.cliente.documento != ref.cliente.documento:
            raise ReglaComprobanteIncumplida("El cliente de la nota debe ser el del comprobante que modifica.",
                                             campo="cliente")
        if self.moneda is not ref.moneda:
            raise ReglaComprobanteIncumplida("La moneda de la nota debe ser la del comprobante que modifica.",
                                             campo="moneda")
        if self.fecha_emision < ref.fecha_emision:
            raise ReglaComprobanteIncumplida("La nota no puede ser anterior al comprobante que modifica.",
                                             campo="fecha_emision")
        if self.tipo is TipoComprobante.NOTA_CREDITO:
            if not isinstance(self.motivo, MotivoNotaCredito):
                raise ReglaComprobanteIncumplida("El motivo de una nota de crédito sale del Catálogo 09.",
                                                 campo="motivo")
            disponible = ref.totales.importe_total - total_notas_credito_previas
            if self.totales.importe_total > disponible:
                raise ReglaComprobanteIncumplida(
                    f"La nota de crédito ({self.totales.importe_total}) excede el saldo no acreditado de "
                    f"{ref.serie_numero} ({disponible}).",
                    campo="lineas",
                )
        elif not isinstance(self.motivo, MotivoNotaDebito):
            raise ReglaComprobanteIncumplida("El motivo de una nota de débito sale del Catálogo 10.", campo="motivo")
