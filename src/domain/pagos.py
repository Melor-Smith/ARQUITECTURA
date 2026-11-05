"""Forma de pago de la factura: Contado o Crédito con cuotas (RS 193-2020/SUNAT).

En una venta al crédito, la factura debe informar el monto neto pendiente de pago y cada
cuota con su importe y fecha de vencimiento. ABC vende al crédito a bodegas y
distribuidores, por eso el dato es parte del dominio y no un adorno del XML.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from src.domain.errores import ErrorDominio
from src.domain.tributos import CERO, redondear

MAXIMO_CUOTAS = 60


class FormaPagoInvalida(ErrorDominio):
    codigo = "ERR-SUNAT-FORMA-PAGO"


class TipoFormaPago(str, Enum):
    CONTADO = "Contado"  # valores literales de cbc:PaymentMeansID
    CREDITO = "Credito"


@dataclass(frozen=True, slots=True)
class Cuota:
    monto: Decimal
    fecha_vencimiento: dt.date


@dataclass(frozen=True, slots=True)
class FormaPago:
    tipo: TipoFormaPago
    cuotas: tuple[Cuota, ...] = ()

    @classmethod
    def contado(cls) -> FormaPago:
        return cls(TipoFormaPago.CONTADO)

    @property
    def es_credito(self) -> bool:
        return self.tipo is TipoFormaPago.CREDITO

    @property
    def monto_pendiente(self) -> Decimal:
        return redondear(sum((c.monto for c in self.cuotas), CERO))

    @property
    def fecha_vencimiento(self) -> dt.date | None:
        """La última cuota: es la fecha de vencimiento que se anota en el campo 5 del 14.1."""
        return self.cuotas[-1].fecha_vencimiento if self.cuotas else None

    def validar(self, *, importe_total: Decimal, fecha_emision: dt.date) -> None:
        if not self.es_credito:
            if self.cuotas:
                raise FormaPagoInvalida("Una venta al contado no lleva cuotas.", campo="forma_pago.cuotas")
            return
        if not self.cuotas:
            raise FormaPagoInvalida("Una venta al crédito requiere al menos una cuota.", campo="forma_pago.cuotas")
        if len(self.cuotas) > MAXIMO_CUOTAS:
            raise FormaPagoInvalida(f"Se admiten como máximo {MAXIMO_CUOTAS} cuotas.", campo="forma_pago.cuotas")
        anterior = fecha_emision
        for i, cuota in enumerate(self.cuotas):
            campo = f"forma_pago.cuotas[{i}]"
            if cuota.monto <= CERO:
                raise FormaPagoInvalida("El monto de cada cuota debe ser mayor a 0.", campo=f"{campo}.monto")
            if cuota.fecha_vencimiento <= anterior:
                raise FormaPagoInvalida(
                    "Cada cuota debe vencer después de la fecha de emisión y de la cuota anterior.",
                    campo=f"{campo}.fecha_vencimiento",
                )
            anterior = cuota.fecha_vencimiento
        if self.monto_pendiente != importe_total:
            raise FormaPagoInvalida(
                f"La suma de las cuotas ({self.monto_pendiente}) debe ser igual al monto pendiente de pago "
                f"({importe_total}); en esta versión no se aplican detracciones ni retenciones.",
                campo="forma_pago.cuotas",
            )
