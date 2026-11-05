"""Reglas tributarias: IGV, ISC (Catálogo 08) e ICBPER, siempre con ``Decimal``.

El cliente de la API nunca envía montos de impuestos: los calcula este módulo.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.domain.catalogos import SistemaISC
from src.domain.errores import ConfiguracionIscInvalida

CERO = Decimal("0")
CENTIMO = Decimal("0.01")

#: TUO de la Ley del IGV: 16 % IGV + 2 % IPM.
TASA_IGV = Decimal("0.18")

#: Art. 56 inciso c) del TUO de la Ley del IGV e ISC: en el sistema de precios de venta
#: al público la base imponible es el precio sugerido multiplicado por 0.847.
FACTOR_BASE_PRECIO_VENTA_PUBLICO = Decimal("0.847")

#: Ley 30884, tasas del ICBPER por bolsa según el año de emisión.
_TASAS_ICBPER: tuple[tuple[int, Decimal], ...] = (
    (2023, Decimal("0.50")),
    (2022, Decimal("0.40")),
    (2021, Decimal("0.30")),
    (2020, Decimal("0.20")),
    (2019, Decimal("0.10")),
)


def redondear(monto: Decimal) -> Decimal:
    """Redondeo comercial a 2 decimales (mitad hacia arriba)."""
    return monto.quantize(CENTIMO, rounding=ROUND_HALF_UP)


def tasa_icbper(fecha: dt.date) -> Decimal:
    for desde, tasa in _TASAS_ICBPER:
        if fecha.year >= desde:
            return tasa
    raise ConfiguracionIscInvalida(
        "El ICBPER no existía antes de agosto de 2019.", codigo="ERR-SUNAT-ICBPER"
    )


@dataclass(frozen=True, slots=True)
class ConfiguracionISC:
    """Datos que el cliente envía para el ISC de una línea; el monto lo calcula el dominio.

    * 01 Al valor: ``tasa`` sobre el valor de venta.
    * 02 Monto fijo: ``monto_fijo`` por unidad vendida.
    * 03 Precio de venta al público: ``tasa`` sobre (precio sugerido x 0.847) por unidad.
    """

    sistema: SistemaISC
    tasa: Decimal | None = None
    monto_fijo: Decimal | None = None
    precio_venta_publico: Decimal | None = None

    def __post_init__(self) -> None:
        def exigir(condicion: bool, mensaje: str) -> None:
            if not condicion:
                raise ConfiguracionIscInvalida(
                    f"ISC sistema {self.sistema.value} ({self.sistema.descripcion}): {mensaje}",
                    campo="isc",
                )

        if self.sistema is SistemaISC.AL_VALOR:
            exigir(self.tasa is not None and CERO < self.tasa <= 1, "requiere 'tasa' entre 0 y 1.")
            exigir(self.monto_fijo is None and self.precio_venta_publico is None,
                   "solo admite 'tasa'.")
        elif self.sistema is SistemaISC.MONTO_FIJO:
            exigir(self.monto_fijo is not None and self.monto_fijo > CERO, "requiere 'monto_fijo' mayor a 0.")
            exigir(self.tasa is None and self.precio_venta_publico is None,
                   "solo admite 'monto_fijo'.")
        else:
            exigir(self.tasa is not None and CERO < self.tasa <= 1, "requiere 'tasa' entre 0 y 1.")
            exigir(self.precio_venta_publico is not None and self.precio_venta_publico > CERO,
                   "requiere 'precio_venta_publico' mayor a 0.")
            exigir(self.monto_fijo is None, "no admite 'monto_fijo'.")

    def calcular(self, cantidad: Decimal, valor_venta: Decimal) -> tuple[Decimal, Decimal]:
        """Devuelve ``(base_imponible, monto)`` del ISC, ambos redondeados a 2 decimales."""
        if self.sistema is SistemaISC.AL_VALOR:
            base = valor_venta
            monto = base * self.tasa  # type: ignore[operator]
        elif self.sistema is SistemaISC.MONTO_FIJO:
            base = valor_venta
            monto = cantidad * self.monto_fijo  # type: ignore[operator]
        else:
            base = cantidad * self.precio_venta_publico * FACTOR_BASE_PRECIO_VENTA_PUBLICO  # type: ignore[operator]
            monto = base * self.tasa  # type: ignore[operator]
        return redondear(base), redondear(monto)

    @property
    def tasa_porcentual(self) -> Decimal | None:
        return None if self.tasa is None else redondear(self.tasa * 100)
