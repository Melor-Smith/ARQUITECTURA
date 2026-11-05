"""Inventario permanente en unidades físicas (materia prima del formato PLE 12.1).

La ficha del sistema antiguo (fecha, ingreso, salida, producto, nro_documento) no tiene
lo que pide SUNAT: falta el establecimiento, el tipo de existencia (tabla 5), el tipo de
operación (tabla 12), un documento de soporte tipificado (tabla 10), la unidad (tabla 6)
y el saldo. Este módulo completa esos datos sin convertir un vale interno en un número
de comprobante SUNAT.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from src.domain.catalogos import (
    SentidoMovimiento,
    TipoDocumentoPLE,
    TipoExistencia,
    TipoOperacionInventario,
    UnidadMedida,
)
from src.domain.errores import ConflictoDominio, ErrorDominio, FichaLegadoInvalida, SaldoInsuficiente
from src.domain.tributos import CERO


@dataclass(frozen=True, slots=True)
class Producto:
    codigo: str
    descripcion: str
    unidad: UnidadMedida
    tipo_existencia: TipoExistencia = TipoExistencia.MERCADERIAS


def normalizar_texto(texto: str) -> str:
    """Normaliza la glosa libre del sistema antiguo para poder homologarla."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sin_tildes).strip().casefold()


@dataclass(frozen=True, slots=True)
class Homologacion:
    """Equivalencia entre la glosa del sistema antiguo y un producto del catálogo.

    ``factor_conversion`` indica cuántas unidades de inventario representa una unidad del
    sistema antiguo; por ejemplo, 1 "Saco de Arroz Extra 50kg" equivale a 50 KGM.
    """

    texto_legado: str
    codigo_producto: str
    factor_conversion: Decimal = Decimal("1")

    @property
    def clave(self) -> str:
        return normalizar_texto(self.texto_legado)


@dataclass(frozen=True, slots=True)
class DocumentoSoporte:
    """Documento que sustenta un movimiento de inventario (campos 10 a 13 del formato 12.1)."""

    tipo: TipoDocumentoPLE
    serie: str
    numero: str
    fecha: dt.date

    @classmethod
    def desde_documento_interno(cls, nro_documento: str, fecha: dt.date) -> DocumentoSoporte:
        """Un vale o guía interna es un documento tipo 00 (otros), no una guía de remisión (09)."""
        cabeza, separador, cola = nro_documento.strip().rpartition("-")
        if separador and cola.isdigit() and cabeza:
            return cls(TipoDocumentoPLE.OTROS, cabeza[:20], cola[:20], fecha)
        return cls(TipoDocumentoPLE.OTROS, "0", nro_documento.strip()[:20], fecha)

    @property
    def referencia(self) -> str:
        return f"{self.serie}-{self.numero}"


# --- clasificación del nro_documento del sistema antiguo ------------------------------
@dataclass(frozen=True, slots=True)
class DocumentoClasificado:
    documento: DocumentoSoporte
    regla: str  # nombre de la regla de reconocimiento que se aplicó
    observacion: str | None = None  # si no es None, el dato se migró pero requiere revisión humana


_PREFIJOS_INTERNOS = ("VALE", "GUIA-INT", "GI-", "NOTA-INGRESO", "NI-", "PEDIDO", "PED-")
_RECONOCEDORES: tuple[tuple[str, re.Pattern[str], TipoDocumentoPLE | None], ...] = (
    # (nombre, patrón, tipo); tipo None = se decide por la letra de la serie
    ("COMPROBANTE_ELECTRONICO", re.compile(r"^([FB][A-Z0-9]{3})-0*(\d{1,8})$"), None),
    ("FACTURA_FISICA", re.compile(r"^(?:FACTURA|FACT|FAC|FT)[\s.:#-]*(\d{1,4})-0*(\d{1,8})$"),
     TipoDocumentoPLE.FACTURA),
    ("BOLETA_FISICA", re.compile(r"^(?:BOLETA|BOL|BV)[\s.:#-]*(\d{1,4})-0*(\d{1,8})$"), TipoDocumentoPLE.BOLETA),
    ("GUIA_REMISION", re.compile(r"^(?:GUIA|GR|G/R|GRR)[\s.:#-]*([A-Z0-9]{1,4})-0*(\d{1,8})$"),
     TipoDocumentoPLE.GUIA_REMISION_REMITENTE),
)
_SIN_DOCUMENTO = {"", "-", "S/N", "SN", "S.N.", "SIN DOC", "SIN DOCUMENTO"}


def clasificar_documento_legado(texto: str, fecha: dt.date) -> DocumentoClasificado:
    """Reconoce qué documento es realmente el ``nro_documento`` de una ficha antigua.

    El orden importa: primero los documentos internos (para que ``GUIA-INT-0015`` no se
    confunda con una guía de remisión), luego los comprobantes y guías reconocibles y, al
    final, lo que no se reconoce, que se conserva como documento interno con observación.
    """
    normalizado = re.sub(r"\s+", " ", texto).strip().upper()
    if normalizado in _SIN_DOCUMENTO:
        return DocumentoClasificado(
            DocumentoSoporte(TipoDocumentoPLE.OTROS, "SN", fecha.strftime("%Y%m%d"), fecha), "SIN_DOCUMENTO",
            "La ficha no tiene documento de soporte; se registró como documento interno sin número.",
        )
    if normalizado.startswith(_PREFIJOS_INTERNOS):
        return DocumentoClasificado(DocumentoSoporte.desde_documento_interno(normalizado, fecha), "DOCUMENTO_INTERNO")
    for nombre, patron, tipo in _RECONOCEDORES:
        coincidencia = patron.match(normalizado)
        if coincidencia:
            serie, numero = coincidencia.groups()
            if tipo is None:
                tipo = TipoDocumentoPLE.FACTURA if serie.startswith("F") else TipoDocumentoPLE.BOLETA
            elif serie.isdigit():
                serie = serie.zfill(4)  # series físicas numéricas: 001 → 0001
            return DocumentoClasificado(DocumentoSoporte(tipo, serie, numero, fecha), nombre)
    return DocumentoClasificado(
        DocumentoSoporte.desde_documento_interno(normalizado, fecha), "NO_RECONOCIDO",
        f"No se reconoció el documento '{texto.strip()}'; se registró como documento interno (tabla 10, tipo 00).",
    )


_FORMATOS_FECHA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y")


def parsear_fecha_legado(texto: str) -> dt.date:
    """El sistema antiguo guardaba fechas escritas a mano en varios formatos."""
    limpio = texto.strip()
    for formato in _FORMATOS_FECHA:
        try:
            return dt.datetime.strptime(limpio, formato).date()
        except ValueError:
            continue
    raise FichaLegadoInvalida(
        f"La fecha '{texto}' no es válida (formatos aceptados: AAAA-MM-DD, DD/MM/AAAA, DD-MM-AAAA, DD.MM.AAAA, "
        "DD/MM/AA).", codigo="ERR-LEGADO-FECHA", campo="fecha",
    )


@dataclass(frozen=True, slots=True)
class MovimientoInventario:
    id: str
    fecha: dt.date
    establecimiento: str
    producto: Producto
    tipo_operacion: TipoOperacionInventario
    documento: DocumentoSoporte
    entrada: Decimal
    salida: Decimal
    saldo: Decimal
    glosa: str = ""

    @property
    def sentido(self) -> SentidoMovimiento:
        return SentidoMovimiento.ENTRADA if self.entrada > CERO else SentidoMovimiento.SALIDA


@dataclass(eq=False)
class Kardex:
    """Kardex en unidades físicas de un producto en un establecimiento."""

    establecimiento: str
    producto: Producto
    _movimientos: list[MovimientoInventario] = field(default_factory=list)

    @property
    def movimientos(self) -> tuple[MovimientoInventario, ...]:
        return tuple(self._movimientos)

    @property
    def saldo(self) -> Decimal:
        return self._movimientos[-1].saldo if self._movimientos else CERO

    def verificar(
        self,
        *,
        fecha: dt.date,
        tipo_operacion: TipoOperacionInventario,
        sentido: SentidoMovimiento,
        cantidad: Decimal,
    ) -> None:
        """Comprueba, sin modificar el Kardex, que el movimiento puede registrarse."""
        if cantidad <= CERO:
            raise ErrorDominio("La cantidad del movimiento debe ser mayor a 0.", codigo="ERR-KARDEX-CANTIDAD")
        if sentido not in tipo_operacion.sentidos_permitidos:
            raise ErrorDominio(
                f"El tipo de operación {tipo_operacion.value} ({tipo_operacion.descripcion}) no admite "
                f"movimientos de {sentido.value.lower()}.",
                codigo="ERR-KARDEX-TIPO-OPERACION", campo="tipo_operacion",
            )
        if self._movimientos and fecha < self._movimientos[-1].fecha:
            raise ErrorDominio(
                f"El Kardex de {self.producto.codigo} ya tiene movimientos al {self._movimientos[-1].fecha}; "
                "no se pueden registrar movimientos con fecha anterior.",
                codigo="ERR-KARDEX-FECHA", campo="fecha",
            )
        if sentido is SentidoMovimiento.SALIDA and cantidad > self.saldo:
            raise SaldoInsuficiente(
                f"Saldo insuficiente de {self.producto.codigo} en el establecimiento {self.establecimiento}: "
                f"disponible {self.saldo} {self.producto.unidad.value}, solicitado {cantidad}.",
            )

    def registrar(
        self,
        *,
        id_movimiento: str,
        fecha: dt.date,
        tipo_operacion: TipoOperacionInventario,
        sentido: SentidoMovimiento,
        cantidad: Decimal,
        documento: DocumentoSoporte,
        glosa: str = "",
    ) -> MovimientoInventario:
        self.verificar(fecha=fecha, tipo_operacion=tipo_operacion, sentido=sentido, cantidad=cantidad)
        if tipo_operacion.exige_comprobante and documento.tipo is TipoDocumentoPLE.OTROS:
            raise ErrorDominio(
                f"La operación {tipo_operacion.value} ({tipo_operacion.descripcion}) debe sustentarse con un "
                f"comprobante de pago o una guía de remisión, no con un documento interno "
                f"('{documento.referencia}'). Use la operación 99 (Otros) o adjunte el comprobante.",
                codigo="ERR-KARDEX-DOCUMENTO-OPERACION", campo="tipo_operacion",
            )
        es_entrada = sentido is SentidoMovimiento.ENTRADA
        movimiento = MovimientoInventario(
            id=id_movimiento,
            fecha=fecha,
            establecimiento=self.establecimiento,
            producto=self.producto,
            tipo_operacion=tipo_operacion,
            documento=documento,
            entrada=cantidad if es_entrada else CERO,
            salida=CERO if es_entrada else cantidad,
            saldo=self.saldo + cantidad if es_entrada else self.saldo - cantidad,
            glosa=glosa,
        )
        self._movimientos.append(movimiento)
        return movimiento


@dataclass(frozen=True, slots=True)
class FichaLegado:
    """Registro tal como existe en el sistema antiguo del almacén."""

    fecha: dt.date
    ingreso: Decimal
    salida: Decimal
    producto: str
    nro_documento: str

    def __post_init__(self) -> None:
        if self.ingreso < CERO or self.salida < CERO:
            raise FichaLegadoInvalida("Ingreso y salida no pueden ser negativos.")
        if self.ingreso == CERO and self.salida == CERO:
            raise FichaLegadoInvalida(
                "La ficha no registra movimiento: ingreso y salida son 0.", codigo="ERR-LEGADO-SIN-MOVIMIENTO"
            )
        if self.ingreso > CERO and self.salida > CERO:
            raise FichaLegadoInvalida(
                "La ficha registra ingreso y salida a la vez; deben migrarse como dos movimientos.",
                codigo="ERR-LEGADO-AMBIGUA",
            )
        if not self.producto.strip() or not self.nro_documento.strip():
            raise FichaLegadoInvalida("Producto y número de documento son obligatorios.")

    @property
    def sentido(self) -> SentidoMovimiento:
        return SentidoMovimiento.ENTRADA if self.ingreso > CERO else SentidoMovimiento.SALIDA

    @property
    def cantidad(self) -> Decimal:
        return self.ingreso if self.ingreso > CERO else self.salida


class EstadoMigracion(str, Enum):
    PENDIENTE_FACTURACION = "PENDIENTE_FACTURACION"  # salida por venta aún sin comprobante electrónico
    FACTURADA = "FACTURADA"
    FACTURADA_EN_SISTEMA_ANTIGUO = "FACTURADA_EN_SISTEMA_ANTIGUO"  # la salida ya tenía factura o boleta física
    NO_REQUIERE_FACTURA = "NO_REQUIERE_FACTURA"  # ingresos, mermas, transferencias, etc.


@dataclass(eq=False)
class MigracionLegado:
    id: str
    ficha: FichaLegado
    homologacion: Homologacion
    movimiento: MovimientoInventario
    estado: EstadoMigracion
    comprobante: str | None = None  # "01/F001-1" cuando se factura
    regla_documento: str = "DOCUMENTO_INTERNO"
    observaciones: tuple[str, ...] = ()  # supuestos que una persona debe revisar
    clave: str = ""  # identifica la ficha para detectar duplicados (normalmente, su nro_documento)

    @property
    def identificador(self) -> str:
        return self.clave or self.ficha.nro_documento

    def asegurar_pendiente(self) -> None:
        if self.estado is not EstadoMigracion.PENDIENTE_FACTURACION:
            detalle = f", facturado en {self.comprobante}" if self.comprobante else ""
            raise ConflictoDominio(
                f"El documento legado '{self.ficha.nro_documento}' no está pendiente de facturación "
                f"(estado {self.estado.value}{detalle}).",
                codigo="ERR-LEGADO-YA-FACTURADO",
            )

    def marcar_facturada(self, comprobante: str) -> None:
        self.asegurar_pendiente()
        self.estado = EstadoMigracion.FACTURADA
        self.comprobante = comprobante

    def revertir_facturacion(self) -> None:
        """Se usa cuando la OSE rechaza el comprobante que facturaba esta salida."""
        if self.estado is EstadoMigracion.FACTURADA:
            self.estado = EstadoMigracion.PENDIENTE_FACTURACION
            self.comprobante = None
