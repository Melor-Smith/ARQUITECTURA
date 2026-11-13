"""Comandos de entrada de los casos de uso (puertos de entrada).

Son dataclasses puras: el adaptador HTTP traduce sus DTO de Pydantic a estos comandos,
de modo que la aplicación no depende de FastAPI ni de Pydantic. Fíjese que ningún
comando trae montos de impuestos, totales ni correlativo: todo eso lo calcula o lo
asigna el servidor.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from src.domain.catalogos import (
    AfectacionIGV,
    Moneda,
    MotivoNotaCredito,
    MotivoNotaDebito,
    SistemaISC,
    TipoComprobante,
    TipoDocumentoIdentidad,
    TipoOperacionInventario,
    UnidadMedida,
)
from src.domain.pagos import TipoFormaPago


@dataclass(frozen=True, slots=True)
class IscCmd:
    sistema: SistemaISC
    tasa: Decimal | None = None
    monto_fijo: Decimal | None = None
    precio_venta_publico: Decimal | None = None


@dataclass(frozen=True, slots=True)
class LineaCmd:
    descripcion: str
    unidad_medida: UnidadMedida
    cantidad: Decimal
    valor_unitario: Decimal
    afectacion_igv: AfectacionIGV
    codigo_producto: str | None = None
    isc: IscCmd | None = None
    aplica_icbper: bool = False


@dataclass(frozen=True, slots=True)
class ClienteCmd:
    tipo_documento: TipoDocumentoIdentidad
    numero_documento: str
    nombre: str
    direccion: str | None = None


@dataclass(frozen=True, slots=True)
class ReferenciaCmd:
    tipo: TipoComprobante
    serie_numero: str


@dataclass(frozen=True, slots=True)
class CuotaCmd:
    monto: Decimal
    fecha_vencimiento: dt.date


@dataclass(frozen=True, slots=True)
class FormaPagoCmd:
    tipo: TipoFormaPago
    cuotas: tuple[CuotaCmd, ...] = ()


@dataclass(frozen=True, slots=True)
class EmitirComprobanteCmd:
    tipo: TipoComprobante
    serie: str
    cliente: ClienteCmd
    lineas: tuple[LineaCmd, ...]
    moneda: Moneda = Moneda.PEN
    tipo_cambio: Decimal | None = None
    fecha_emision: dt.date | None = None
    documentos_legado: tuple[str, ...] = ()
    referencia: ReferenciaCmd | None = None
    motivo: MotivoNotaCredito | MotivoNotaDebito | None = None
    sustento: str | None = None
    forma_pago: FormaPagoCmd | None = None
    clave_idempotencia: str | None = None
    huella: str | None = None  # resumen del contenido, para detectar reutilización de la clave


@dataclass(frozen=True, slots=True)
class GenerarXmlVentaCmd:
    """Venta registrada en el formulario web (Taller 2): de aquí sale el XML UBL 2.1.

    Solo factura o boleta. Igual que en la emisión, no trae impuestos, totales ni correlativo:
    los calcula el dominio. ``incluir_firma`` es opcional porque el XML se valida sin firma.
    """

    tipo: TipoComprobante
    serie: str
    cliente: ClienteCmd
    lineas: tuple[LineaCmd, ...]
    incluir_firma: bool = False


@dataclass(frozen=True, slots=True)
class MigrarFichaLegadoCmd:
    fecha: dt.date | str  # texto tal como venía en el sistema antiguo; el dominio lo interpreta
    ingreso: Decimal
    salida: Decimal
    producto: str
    nro_documento: str
    codigo_producto: str | None = None
    factor_conversion: Decimal | None = None
    tipo_operacion: TipoOperacionInventario | None = None
    establecimiento: str | None = None
