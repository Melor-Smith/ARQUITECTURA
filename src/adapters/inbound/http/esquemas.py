"""DTO del contrato HTTP (Pydantic v2). De aquí se genera ``specs/contracts/openapi.yaml``.

Reglas del contrato:

* ``extra="forbid"``: si el cliente envía ``igv_item``, ``totales`` o ``correlativo``, la
  solicitud se rechaza con 400. Los impuestos y el correlativo los decide el servidor.
* Los importes se reciben como número o cadena y se devuelven como cadena decimal, para
  no perder precisión con ``float``.
* Validar el formato es tarea del DTO (400); las reglas de negocio son del dominio (422).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.domain.catalogos import (
    AfectacionIGV,
    Moneda,
    MotivoNotaCredito,
    MotivoNotaDebito,
    SistemaISC,
    TipoDocumentoIdentidad,
    TipoOperacionInventario,
    UnidadMedida,
)
from src.domain.comprobante import EstadoComprobante
from src.domain.inventario import EstadoMigracion

PATRON_SERIE = r"^[FB][A-Z0-9]{3}$"
PATRON_SERIE_NUMERO = r"^[FB][A-Z0-9]{3}-[0-9]{1,8}$"


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


Cantidad = Annotated[Decimal, Field(gt=0, max_digits=22, decimal_places=10)]
Importe = Annotated[Decimal, Field(gt=0, max_digits=22, decimal_places=10)]


# --- comprobantes: entrada --------------------------------------------------------------
class IscEntrada(_Entrada):
    """Configuración del ISC según el Catálogo 08. El monto lo calcula el servidor."""

    sistema: SistemaISC = Field(description="Catálogo 08: 01 al valor, 02 monto fijo, 03 precio de venta al público.")
    tasa: Decimal | None = Field(None, gt=0, le=1, decimal_places=4, description="Sistemas 01 y 03. Ej.: 0.20")
    monto_fijo: Decimal | None = Field(None, gt=0, decimal_places=4, description="Sistema 02, por unidad.")
    precio_venta_publico: Decimal | None = Field(None, gt=0, decimal_places=4, description="Sistema 03, por unidad.")


class LineaEntrada(_Entrada):
    codigo_producto: str | None = Field(None, max_length=30, pattern=r"^[A-Z0-9-]+$", examples=["AB-ARR-001"],
                                        description="Si se envía, debe existir en el catálogo y mueve el Kardex.")
    descripcion: str = Field(min_length=1, max_length=500, examples=["Arroz extra a granel"])
    unidad_medida: UnidadMedida = Field(description="Catálogo 03 (UN/ECE Rec. 20). Va en el atributo unitCode.")
    cantidad: Cantidad = Field(examples=["50"])
    valor_unitario: Importe = Field(description="Valor unitario SIN impuestos.", examples=["4.20"])
    afectacion_igv: AfectacionIGV = Field(AfectacionIGV.GRAVADO_ONEROSA, description="Catálogo 07.")
    isc: IscEntrada | None = None
    aplica_icbper: bool = Field(False, description="True si la línea son bolsas plásticas (Ley 30884).")


class ClienteEntrada(_Entrada):
    tipo_documento: TipoDocumentoIdentidad = Field(description="Catálogo 06.")
    numero_documento: str = Field(min_length=1, max_length=15, examples=["20123456786"])
    nombre: str = Field(min_length=1, max_length=500, examples=["DISTRIBUIDORA EL SOL S.A.C."])
    direccion: str | None = Field(None, max_length=200)


class _ComprobanteEntrada(_Entrada):
    serie: str = Field(pattern=PATRON_SERIE, examples=["F001"],
                       description="Serie de 4 caracteres. El correlativo lo asigna el servidor.")
    fecha_emision: dt.date | None = Field(None, description="Por defecto, la fecha actual del servidor (UTC-5).")
    moneda: Moneda = Field(Moneda.PEN, description="Catálogo 02.")
    tipo_cambio: Decimal | None = Field(None, gt=0, max_digits=8, decimal_places=3,
                                        description="Obligatorio si la moneda es USD.")
    cliente: ClienteEntrada
    lineas: list[LineaEntrada] = Field(min_length=1, max_length=500)


class CuotaEntrada(_Entrada):
    monto: Importe = Field(examples=["179.95"])
    fecha_vencimiento: dt.date


class FormaPagoEntrada(_Entrada):
    """RS 193-2020. Al crédito, la suma de las cuotas debe igualar el importe total que calcula el servidor."""

    tipo: Literal["CONTADO", "CREDITO"] = "CONTADO"
    cuotas: list[CuotaEntrada] = Field(default_factory=list, max_length=60)


class FacturaEntrada(_ComprobanteEntrada):
    tipo_comprobante: Literal["01"] = Field(description="Catálogo 01: factura.")
    forma_pago: FormaPagoEntrada = Field(default_factory=FormaPagoEntrada,
                                         description="Contado por defecto. Solo las facturas la informan.")
    documentos_legado: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(
        default_factory=list, max_length=50,
        description="Vales del sistema antiguo ya migrados que esta venta factura (cac:AdditionalDocumentReference, "
                    "Catálogo 12 tipo 99).",
    )


class BoletaEntrada(_ComprobanteEntrada):
    tipo_comprobante: Literal["03"] = Field(description="Catálogo 01: boleta de venta.")
    documentos_legado: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(
        default_factory=list, max_length=50)


class ReferenciaEntrada(_Entrada):
    tipo_comprobante: Literal["01", "03"]
    serie_numero: str = Field(pattern=PATRON_SERIE_NUMERO, examples=["F001-1"])


class NotaCreditoEntrada(_ComprobanteEntrada):
    tipo_comprobante: Literal["07"] = Field(description="Catálogo 01: nota de crédito.")
    referencia: ReferenciaEntrada
    motivo: MotivoNotaCredito = Field(description="Catálogo 09.")
    sustento: str = Field(min_length=1, max_length=250)


class NotaDebitoEntrada(_ComprobanteEntrada):
    tipo_comprobante: Literal["08"] = Field(description="Catálogo 01: nota de débito.")
    referencia: ReferenciaEntrada
    motivo: MotivoNotaDebito = Field(description="Catálogo 10.")
    sustento: str = Field(min_length=1, max_length=250)


ComprobanteEntrada = Annotated[
    FacturaEntrada | BoletaEntrada | NotaCreditoEntrada | NotaDebitoEntrada,
    Field(discriminator="tipo_comprobante"),
]


# --- comprobantes: salida ---------------------------------------------------------------
class CodigoDescripcion(_Salida):
    codigo: str
    descripcion: str


class TributoLinea(_Salida):
    base: Decimal
    monto: Decimal


class IscLinea(TributoLinea):
    sistema: CodigoDescripcion


class LineaSalida(_Salida):
    numero: int
    codigo_producto: str | None
    descripcion: str
    unidad_medida: str
    cantidad: Decimal
    valor_unitario: Decimal
    precio_unitario: Decimal = Field(description="Con IGV e ISC (cac:PricingReference, tipo de precio 01).")
    valor_venta: Decimal
    afectacion_igv: CodigoDescripcion
    isc: IscLinea | None
    igv: TributoLinea
    icbper: Decimal


class TotalesSalida(_Salida):
    gravadas: Decimal
    exoneradas: Decimal
    inafectas: Decimal
    exportacion: Decimal
    isc: Decimal
    igv: Decimal
    icbper: Decimal
    total_impuestos: Decimal
    valor_venta: Decimal
    importe_total: Decimal


class ParteSalida(_Salida):
    tipo_documento: str
    numero_documento: str
    nombre: str


class ReferenciaSalida(_Salida):
    tipo_comprobante: str
    serie_numero: str


class CdrSalida(_Salida):
    codigo: str
    descripcion: str
    observaciones: list[str]
    fecha_recepcion: dt.datetime


class CuotaSalida(_Salida):
    numero: int
    monto: Decimal
    fecha_vencimiento: dt.date


class FormaPagoSalida(_Salida):
    tipo: Literal["CONTADO", "CREDITO"]
    monto_pendiente: Decimal
    cuotas: list[CuotaSalida]


class EnlacesComprobante(_Salida):
    detalle: str
    xml: str
    envios: str


class ComprobanteSalida(_Salida):
    tipo_comprobante: CodigoDescripcion
    serie: str
    correlativo: int
    serie_numero: str = Field(description="cbc:ID. Serie y correlativo solo se unen al serializar.")
    fecha_emision: dt.date
    hora_emision: dt.time
    moneda: str
    tipo_cambio: Decimal | None
    emisor: ParteSalida
    cliente: ParteSalida
    lineas: list[LineaSalida]
    totales: TotalesSalida
    monto_en_letras: str = Field(description="Leyenda 1000 (Catálogo 52).")
    forma_pago: FormaPagoSalida | None = Field(description="Solo en facturas (RS 193-2020).")
    documentos_legado: list[str]
    referencia: ReferenciaSalida | None
    motivo: CodigoDescripcion | None
    sustento: str | None
    estado: EstadoComprobante = Field(description="Sale del CDR de la OSE; PENDIENTE_ENVIO si la OSE no respondió.")
    hash_cpe: str | None = Field(description="ds:DigestValue de la firma XMLDSig (base64).")
    cdr: CdrSalida | None
    intentos_envio: int
    enlaces: EnlacesComprobante


# --- inventario -------------------------------------------------------------------------
class FichaLegadoEntrada(_Entrada):
    """Ficha tal como existe en el sistema antiguo, más datos opcionales de homologación."""

    fecha: str = Field(min_length=6, max_length=20, examples=["2026-10-15", "15/10/2026"],
                       description="Tal como está en el sistema antiguo. Formatos: AAAA-MM-DD, DD/MM/AAAA, "
                                   "DD-MM-AAAA, DD.MM.AAAA y DD/MM/AA.")
    ingreso: Decimal = Field(ge=0, max_digits=22, decimal_places=4)
    salida: Decimal = Field(ge=0, max_digits=22, decimal_places=4)
    producto: str = Field(min_length=1, max_length=200, examples=["Saco de Azúcar Rubia 50kg"])
    nro_documento: str = Field(min_length=1, max_length=40, examples=["VALE-SALIDA-0042"])
    codigo_producto: str | None = Field(None, max_length=30, pattern=r"^[A-Z0-9-]+$",
                                        description="Solo si la glosa no está en la tabla de homologación.")
    factor_conversion: Decimal | None = Field(None, gt=0, decimal_places=4)
    tipo_operacion: TipoOperacionInventario | None = Field(
        None, description="Tabla 12. Por defecto 01 (venta) para salidas y 02 (compra) para ingresos.")
    establecimiento: str | None = Field(None, pattern=r"^\d{4}$", description="Código de establecimiento anexo SUNAT.")


class DocumentoSoporteSalida(_Salida):
    tipo: CodigoDescripcion = Field(description="Tabla 10 del PLE (00 = documento interno).")
    serie: str
    numero: str
    fecha: dt.date


class MovimientoSalida(_Salida):
    id: str
    fecha: dt.date
    establecimiento: str
    codigo_producto: str
    tipo_operacion: CodigoDescripcion = Field(description="Tabla 12 del PLE.")
    documento: DocumentoSoporteSalida
    entrada: Decimal
    salida: Decimal
    saldo: Decimal
    glosa: str


class HomologacionSalida(_Salida):
    texto_legado: str
    codigo_producto: str
    factor_conversion: Decimal


class MigracionSalida(_Salida):
    id_migracion: str
    clave: str = Field(description="Identifica la ficha (su nro_documento, o un resumen si no tenía documento).")
    nro_documento_legado: str
    regla_documento: str = Field(description="Cómo se reconoció el nro_documento: COMPROBANTE_ELECTRONICO, "
                                             "FACTURA_FISICA, BOLETA_FISICA, GUIA_REMISION, DOCUMENTO_INTERNO, "
                                             "SIN_DOCUMENTO o NO_RECONOCIDO.")
    estado: EstadoMigracion
    comprobante: str | None = Field(description="tipo/serie-número del comprobante que la facturó.")
    observaciones: list[str] = Field(description="Supuestos que una persona debe revisar (no bloquean).")
    homologacion: HomologacionSalida
    movimiento: MovimientoSalida


class LoteEntrada(_Entrada):
    fichas: list[FichaLegadoEntrada] = Field(min_length=1, max_length=5000)


class ResultadoFichaSalida(_Salida):
    indice: int
    nro_documento: str
    estado: Literal["MIGRADA", "OBSERVADA", "DUPLICADA"]
    codigo: str | None
    mensaje: str | None
    migracion: MigracionSalida | None


class ConciliacionSalida(_Salida):
    establecimiento: str
    codigo_producto: str
    saldo_inicial: Decimal
    entradas: Decimal
    salidas: Decimal
    saldo_final: Decimal
    cuadra: bool


class ResumenLoteSalida(_Salida):
    total: int
    migradas: int
    observadas: int
    duplicadas: int
    cuadra: bool


class LoteSalida(_Salida):
    id_lote: str
    procesado_en: dt.datetime
    resumen: ResumenLoteSalida
    conciliacion: list[ConciliacionSalida]
    resultados: list[ResultadoFichaSalida]


class ProductoSalida(_Salida):
    codigo: str
    descripcion: str
    unidad_medida: CodigoDescripcion = Field(description="Catálogo 03 (UNECE).")
    unidad_medida_ple: CodigoDescripcion = Field(description="Tabla 6 del PLE (equivalencia).")
    tipo_existencia: CodigoDescripcion = Field(description="Tabla 5 del PLE.")


class KardexSalida(_Salida):
    establecimiento: str
    producto: ProductoSalida
    saldo_final: Decimal
    movimientos: list[MovimientoSalida]


# --- libros electrónicos ----------------------------------------------------------------
class LibroElectronicoSalida(_Salida):
    formato: str
    nombre_archivo: str
    periodo: str
    filas: list[dict[str, str]] = Field(description="Una fila por anotación, con los campos en orden.")


# --- errores (RFC 9457 application/problem+json) ----------------------------------------
class ErrorCampo(_Salida):
    campo: str
    mensaje: str


class Problema(_Salida):
    type: str = Field(examples=["urn:abc:problema:regla-negocio"])
    title: str
    status: int
    detail: str
    instance: str | None = None
    codigo: str = Field(examples=["ERR-SUNAT-RUC"], description="Código estable para el cliente.")
    errores: list[ErrorCampo] = Field(default_factory=list)


class Salud(_Salida):
    estado: str
    version: str
    version_ubl: str
    modo_ose: str
