"""Monto en letras (leyenda 1000) y forma de pago (RS 193-2020)."""

import datetime as dt
from decimal import Decimal as D

import pytest

from src.domain.catalogos import Moneda
from src.domain.letras import entero_en_letras, importe_en_letras
from src.domain.pagos import Cuota, FormaPago, FormaPagoInvalida, TipoFormaPago


@pytest.mark.parametrize(("n", "letras"), [
    (0, "CERO"), (1, "UNO"), (15, "QUINCE"), (16, "DIECISÉIS"), (21, "VEINTIUNO"), (22, "VEINTIDÓS"),
    (30, "TREINTA"), (45, "CUARENTA Y CINCO"), (100, "CIEN"), (101, "CIENTO UNO"),
    (359, "TRESCIENTOS CINCUENTA Y NUEVE"),
    (500, "QUINIENTOS"), (1000, "MIL"), (1001, "MIL UNO"), (2021, "DOS MIL VEINTIUNO"), (21000, "VEINTIÚN MIL"),
    (31000, "TREINTA Y UN MIL"), (100000, "CIEN MIL"), (1_000_000, "UN MILLÓN"),
    (2_500_000, "DOS MILLONES QUINIENTOS MIL"),
    (21_000_000, "VEINTIÚN MILLONES"),
])
def test_entero_en_letras(n, letras):
    assert entero_en_letras(n) == letras


def test_importe_con_centimos_y_moneda():
    assert importe_en_letras(D("359.90"), Moneda.PEN) == "TRESCIENTOS CINCUENTA Y NUEVE CON 90/100 SOLES"
    assert importe_en_letras(D("1.05"), Moneda.USD) == "UNO CON 05/100 DÓLARES AMERICANOS"


HOY = dt.date(2026, 10, 22)


def credito(*cuotas: tuple[str, dt.date]) -> FormaPago:
    return FormaPago(TipoFormaPago.CREDITO, tuple(Cuota(D(m), d) for m, d in cuotas))


class TestFormaPago:
    def test_contado(self):
        FormaPago.contado().validar(importe_total=D("100.00"), fecha_emision=HOY)

    def test_credito_valido(self):
        fp = credito(("60.00", dt.date(2026, 11, 22)), ("40.00", dt.date(2026, 12, 22)))
        fp.validar(importe_total=D("100.00"), fecha_emision=HOY)
        assert (fp.monto_pendiente, fp.fecha_vencimiento) == (D("100.00"), dt.date(2026, 12, 22))

    @pytest.mark.parametrize(("forma", "mensaje"), [
        (FormaPago(TipoFormaPago.CREDITO), "al menos una cuota"),
        (FormaPago(TipoFormaPago.CONTADO, (Cuota(D("1"), dt.date(2026, 11, 1)),)), "no lleva cuotas"),
        (credito(("100.00", HOY)), "vencer después"),
        (credito(("50.00", dt.date(2026, 12, 1)), ("50.00", dt.date(2026, 11, 1))), "vencer después"),
        (credito(("90.00", dt.date(2026, 11, 1))), "suma de las cuotas"),
        (credito(("0", dt.date(2026, 11, 1)), ("100.00", dt.date(2026, 12, 1))), "mayor a 0"),
    ])
    def test_reglas(self, forma, mensaje):
        with pytest.raises(FormaPagoInvalida, match=mensaje) as error:
            forma.validar(importe_total=D("100.00"), fecha_emision=HOY)
        assert error.value.codigo == "ERR-SUNAT-FORMA-PAGO"
