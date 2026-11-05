"""Reglas cruzadas del agregado Comprobante y su máquina de estados."""

import datetime as dt
from decimal import Decimal as D

import pytest

from src.adapters.outbound.persistencia.semillas import EMISOR_ABC
from src.domain.catalogos import (
    AfectacionIGV,
    Moneda,
    MotivoNotaCredito,
    MotivoNotaDebito,
    TipoComprobante,
    TipoDocumentoIdentidad,
    UnidadMedida,
)
from src.domain.comprobante import BorradorComprobante, Cdr, Cliente, EstadoComprobante, Linea
from src.domain.errores import ConflictoDominio, ErrorDominio, ReglaComprobanteIncumplida
from src.domain.valores import Correlativo, DocumentoIdentidad, Serie

HOY = dt.date(2026, 10, 22)
CLIENTE_RUC = Cliente(DocumentoIdentidad(TipoDocumentoIdentidad.RUC, "20123456786"), "CLIENTE S.A.C.")
CLIENTE_DNI = Cliente(DocumentoIdentidad(TipoDocumentoIdentidad.DNI, "46027897"), "MARIA QUISPE")
CLIENTE_VARIOS = Cliente(DocumentoIdentidad(TipoDocumentoIdentidad.NO_DOMICILIADO, "-"), "CLIENTES VARIOS")


def lineas(valor="100", cantidad="1", afectacion=AfectacionIGV.GRAVADO_ONEROSA):
    return (Linea.calcular(numero=1, descripcion="Producto", unidad=UnidadMedida.UNIDAD, cantidad=D(cantidad),
                           valor_unitario=D(valor), afectacion=afectacion, fecha_emision=HOY),)


def preparar(**cambios) -> BorradorComprobante:
    datos = dict(tipo=TipoComprobante.FACTURA, serie=Serie("F001"), fecha_emision=HOY,
                 hora_emision=dt.time(10, 30), hoy=HOY, plazo_dias=3, moneda=Moneda.PEN, tipo_cambio=None,
                 emisor=EMISOR_ABC, cliente=CLIENTE_RUC, lineas=lineas())
    datos.update(cambios)
    return BorradorComprobante.preparar(**datos)


def factura_aceptada(valor="100"):
    comprobante = preparar(lineas=lineas(valor)).numerar(Correlativo(1))
    comprobante.registrar_firma(b"<xml/>", "digest")
    comprobante.registrar_cdr(Cdr("0", "aceptada", dt.datetime(2026, 10, 22)))
    return comprobante


class TestFacturaYBoleta:
    def test_factura_valida(self):
        assert preparar().totales.importe_total == D("118.00")

    def test_factura_exige_serie_f(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="empiece con F") as e:
            preparar(serie=Serie("B001"))
        assert e.value.codigo == "ERR-SUNAT-SERIE"

    def test_factura_exige_cliente_con_ruc(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="RUC") as e:
            preparar(cliente=CLIENTE_DNI)
        assert e.value.codigo == "ERR-SUNAT-RUC"

    def test_factura_de_exportacion_admite_cliente_no_domiciliado(self):
        borrador = preparar(cliente=CLIENTE_VARIOS, lineas=lineas(afectacion=AfectacionIGV.EXPORTACION))
        assert borrador.totales.exportacion == D("100.00")

    def test_boleta_exige_serie_b(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="empiece con B"):
            preparar(tipo=TipoComprobante.BOLETA, serie=Serie("F001"), cliente=CLIENTE_DNI)

    def test_boleta_con_dni(self):
        assert preparar(tipo=TipoComprobante.BOLETA, serie=Serie("B001"), cliente=CLIENTE_DNI)

    def test_boleta_anonima_hasta_700_soles(self):
        assert preparar(tipo=TipoComprobante.BOLETA, serie=Serie("B001"), cliente=CLIENTE_VARIOS,
                        lineas=lineas("593.22"))  # 593.22 x 1.18 = 700.00

    def test_boleta_anonima_mayor_a_700_soles(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="700"):
            preparar(tipo=TipoComprobante.BOLETA, serie=Serie("B001"), cliente=CLIENTE_VARIOS,
                     lineas=lineas("600"))


class TestMonedaYFecha:
    def test_usd_requiere_tipo_de_cambio(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="tipo_cambio"):
            preparar(moneda=Moneda.USD)

    def test_pen_no_lleva_tipo_de_cambio(self):
        with pytest.raises(ReglaComprobanteIncumplida):
            preparar(tipo_cambio=D("3.75"))

    def test_fecha_futura(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="futura"):
            preparar(fecha_emision=HOY + dt.timedelta(days=1))

    def test_fecha_fuera_de_plazo(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="plazo"):
            preparar(fecha_emision=HOY - dt.timedelta(days=4))


class TestNotas:
    def nota(self, referencia, **cambios):
        datos = dict(tipo=TipoComprobante.NOTA_CREDITO, serie=Serie("FC01"), referencia=referencia,
                     motivo=MotivoNotaCredito.DESCUENTO_GLOBAL, sustento="Descuento por volumen")
        datos.update(cambios)
        return preparar(**datos)

    def test_nota_de_credito_valida(self):
        assert self.nota(factura_aceptada(), lineas=lineas("50")).totales.importe_total == D("59.00")

    def test_nota_sin_referencia(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="referencia"):
            self.nota(None)

    def test_serie_de_la_nota_debe_coincidir_con_la_del_comprobante(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="debe empezar con 'F'"):
            self.nota(factura_aceptada(), serie=Serie("BC01"))

    def test_cliente_debe_ser_el_mismo(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="cliente"):
            self.nota(factura_aceptada(), cliente=Cliente(
                DocumentoIdentidad(TipoDocumentoIdentidad.RUC, "20601234565"), "OTRO S.A.C."))

    def test_no_puede_acreditar_mas_que_el_saldo(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="excede"):
            self.nota(factura_aceptada("100"), lineas=lineas("60"), total_notas_credito_previas=D("50.00"))

    def test_no_modifica_un_comprobante_rechazado(self):
        rechazada = preparar().numerar(Correlativo(1))
        rechazada.registrar_firma(b"<xml/>", "d")
        rechazada.registrar_cdr(Cdr("2335", "alterado", dt.datetime(2026, 10, 22)))
        with pytest.raises(ReglaComprobanteIncumplida, match="rechazado"):
            self.nota(rechazada)

    def test_nota_de_debito_usa_catalogo_10(self):
        with pytest.raises(ReglaComprobanteIncumplida, match="Catálogo 10"):
            self.nota(factura_aceptada(), tipo=TipoComprobante.NOTA_DEBITO, motivo=MotivoNotaCredito.DESCUENTO_GLOBAL)
        assert self.nota(factura_aceptada(), tipo=TipoComprobante.NOTA_DEBITO, serie=Serie("FD01"),
                         motivo=MotivoNotaDebito.INTERESES_MORA)


class TestEstados:
    def test_el_estado_sale_del_cdr(self):
        comprobante = preparar().numerar(Correlativo(1))
        assert comprobante.estado is EstadoComprobante.REGISTRADO
        comprobante.registrar_firma(b"<xml/>", "d")
        comprobante.registrar_envio_fallido()
        assert comprobante.estado is EstadoComprobante.PENDIENTE_ENVIO
        comprobante.registrar_cdr(Cdr("0", "aceptada", dt.datetime(2026, 10, 22)))
        assert comprobante.estado is EstadoComprobante.ACEPTADO
        assert comprobante.intentos_envio == 2

    @pytest.mark.parametrize(("codigo", "observaciones", "estado"), [
        ("0", (), EstadoComprobante.ACEPTADO),
        ("0", ("4252",), EstadoComprobante.ACEPTADO_CON_OBSERVACIONES),
        ("4252", (), EstadoComprobante.ACEPTADO_CON_OBSERVACIONES),
        ("2335", (), EstadoComprobante.RECHAZADO),
    ])
    def test_mapeo_de_codigos_cdr(self, codigo, observaciones, estado):
        assert Cdr(codigo, "x", dt.datetime(2026, 10, 22), observaciones).estado_resultante is estado

    def test_codigos_de_excepcion_no_son_cdr(self):
        with pytest.raises(ErrorDominio):
            Cdr("0306", "No se puede leer", dt.datetime(2026, 10, 22)).estado_resultante  # noqa: B018

    def test_no_se_reenvia_un_comprobante_con_cdr(self):
        with pytest.raises(ConflictoDominio):
            factura_aceptada().asegurar_envio_posible()

    def test_no_se_envia_sin_firma(self):
        with pytest.raises(ConflictoDominio, match="firmado"):
            preparar().numerar(Correlativo(1)).asegurar_envio_posible()
