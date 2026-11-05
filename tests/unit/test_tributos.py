"""Cálculo tributario en el dominio, con Decimal: IGV, ISC (Catálogo 08) e ICBPER."""

import datetime as dt
from decimal import Decimal as D

import pytest

from src.domain.catalogos import AfectacionIGV, SistemaISC, UnidadMedida
from src.domain.comprobante import Linea, Totales
from src.domain.errores import ConfiguracionIscInvalida, ReglaTributariaIncumplida, UnidadMedidaInvalida
from src.domain.tributos import ConfiguracionISC, redondear, tasa_icbper

HOY = dt.date(2026, 10, 22)


def linea(cantidad="1", valor="100", afectacion=AfectacionIGV.GRAVADO_ONEROSA, unidad=UnidadMedida.UNIDAD,
          numero=1, **kwargs) -> Linea:
    return Linea.calcular(numero=numero, descripcion="Producto", unidad=unidad, cantidad=D(cantidad),
                          valor_unitario=D(valor), afectacion=afectacion, fecha_emision=HOY, **kwargs)


class TestIgv:
    def test_gravado_18_por_ciento(self):
        ln = linea("2", "100.00")
        assert (ln.valor_venta, ln.monto_igv, ln.total_tributos) == (D("200.00"), D("36.00"), D("36.00"))

    @pytest.mark.parametrize("afectacion", [AfectacionIGV.EXONERADO_ONEROSA, AfectacionIGV.INAFECTO_ONEROSA,
                                            AfectacionIGV.EXPORTACION])
    def test_no_gravado_no_paga_igv(self, afectacion):
        assert linea(afectacion=afectacion).monto_igv == D("0")

    def test_redondeo_comercial_mitad_hacia_arriba(self):
        assert redondear(D("0.125")) == D("0.13")
        assert redondear(D("0.124")) == D("0.12")

    def test_decimal_evita_errores_de_float(self):
        # Con float, 3 x 0.10 = 0.30000000000000004.
        assert linea("3", "0.10").valor_venta == D("0.30")

    def test_valor_unitario_cero_no_esta_soportado(self):
        with pytest.raises(ReglaTributariaIncumplida, match="gratuitas"):
            linea(valor="0")


class TestIscCatalogo08:
    def test_sistema_01_al_valor_y_el_isc_forma_parte_de_la_base_del_igv(self):
        ln = linea("2", "45.00", isc=ConfiguracionISC(SistemaISC.AL_VALOR, tasa=D("0.20")))
        assert ln.valor_venta == D("90.00")
        assert ln.monto_isc == D("18.00")
        assert ln.base_igv == D("108.00")
        assert ln.monto_igv == D("19.44")

    def test_sistema_02_monto_fijo_por_unidad(self):
        ln = linea("12", "5.50", isc=ConfiguracionISC(SistemaISC.MONTO_FIJO, monto_fijo=D("1.35")))
        assert ln.monto_isc == D("16.20")

    def test_sistema_03_precio_de_venta_al_publico_por_0_847(self):
        ln = linea("4", "9.00", isc=ConfiguracionISC(SistemaISC.PRECIO_VENTA_PUBLICO, tasa=D("0.17"),
                                                        precio_venta_publico=D("12.50")))
        assert ln.base_isc == D("42.35")  # 4 x 12.50 x 0.847
        assert ln.monto_isc == D("7.20")  # 42.35 x 0.17 = 7.1995

    @pytest.mark.parametrize("kwargs", [
        {"sistema": SistemaISC.AL_VALOR},
        {"sistema": SistemaISC.AL_VALOR, "tasa": D("1.5")},
        {"sistema": SistemaISC.AL_VALOR, "tasa": D("0.2"), "monto_fijo": D("1")},
        {"sistema": SistemaISC.MONTO_FIJO},
        {"sistema": SistemaISC.PRECIO_VENTA_PUBLICO, "tasa": D("0.2")},
    ])
    def test_configuraciones_incompletas_o_contradictorias(self, kwargs):
        with pytest.raises(ConfiguracionIscInvalida) as error:
            ConfiguracionISC(**kwargs)
        assert error.value.codigo == "ERR-SUNAT-CAT08"

    def test_exportacion_no_lleva_isc(self):
        with pytest.raises(ReglaTributariaIncumplida):
            linea(afectacion=AfectacionIGV.EXPORTACION, isc=ConfiguracionISC(SistemaISC.AL_VALOR, tasa=D("0.1")))


class TestIcbper:
    @pytest.mark.parametrize(("anio", "tasa"), [(2019, "0.10"), (2020, "0.20"), (2021, "0.30"), (2022, "0.40"),
                                                (2023, "0.50"), (2026, "0.50")])
    def test_tasa_segun_el_anio(self, anio, tasa):
        assert tasa_icbper(dt.date(anio, 12, 1)) == D(tasa)

    def test_monto_por_bolsa(self):
        ln = linea("3", "0.10", aplica_icbper=True)
        assert ln.monto_icbper == D("1.50")

    def test_icbper_exige_unidad_niu(self):
        with pytest.raises(UnidadMedidaInvalida):
            linea(unidad=UnidadMedida.KILOGRAMO, aplica_icbper=True)


class TestTotales:
    def test_totales_salen_de_las_lineas_y_no_del_cliente(self):
        lineas = (
            linea("50", "4.20", unidad=UnidadMedida.KILOGRAMO, numero=1),
            linea("2", "45.00", numero=2, isc=ConfiguracionISC(SistemaISC.AL_VALOR, tasa=D("0.20"))),
            linea("3", "0.10", numero=3, aplica_icbper=True),
            linea("1", "10.00", numero=4, afectacion=AfectacionIGV.EXONERADO_ONEROSA),
        )
        t = Totales.de_lineas(lineas)
        assert t.gravadas == D("300.30")
        assert t.exoneradas == D("10.00")
        assert t.isc == D("18.00")
        assert t.igv == D("57.29")
        assert t.icbper == D("1.50")
        assert t.importe_total == t.valor_venta + t.isc + t.igv + t.icbper == D("387.09")
