"""Generación del TXT del PLE: formato de cada campo, reglas entre campos y contraejemplos."""

from __future__ import annotations

import dataclasses
import datetime as dt
from decimal import Decimal as D

import pytest

from src.domain.libros import FilaInventario121, FilaRegistroVentas141
from src.domain.ple_estructura import (
    ESTRUCTURA_121,
    ESTRUCTURA_141,
    FIN_DE_LINEA,
    EstructuraPleInvalida,
    contenido_txt,
    formatear,
    linea_txt,
    validar_filas,
    validar_linea,
)

FACTURA = FilaRegistroVentas141(
    periodo="20261000", cuo="V202610000001", correlativo_asiento="M1",
    fecha_emision=dt.date(2026, 10, 22), fecha_vencimiento=None, tipo_comprobante="01",
    serie="F001", numero="1", numero_final="", tipo_documento_cliente="6",
    numero_documento_cliente="20601234565", nombre_cliente="BODEGA SAN MARTÍN & HIJOS E.I.R.L.",
    valor_exportacion=D("0"), base_gravada=D("305.00"), descuento_base_gravada=D("0"), igv=D("54.90"),
    descuento_igv=D("0"), importe_exonerado=D("0"), importe_inafecto=D("0"), isc=D("0"), base_ivap=D("0"),
    ivap=D("0"), icbper=D("0"), otros_tributos=D("0"), importe_total=D("359.90"), moneda="PEN",
    tipo_cambio=D("1"), fecha_modificado=None, tipo_modificado="", serie_modificado="",
    numero_modificado="", contrato="", error_tipo_cambio="", indicador_medio_pago="", estado="1",
)

NOTA_CREDITO = dataclasses.replace(
    FACTURA, cuo="V202610000002", correlativo_asiento="M2", tipo_comprobante="07", serie="FC01",
    base_gravada=D("-42.00"), igv=D("-7.56"), importe_total=D("-49.56"),
    fecha_modificado=dt.date(2026, 10, 22), tipo_modificado="01", serie_modificado="F001", numero_modificado="1",
)

SALIDA = FilaInventario121(
    periodo="20261000", cuo="I202610000002", correlativo_asiento="M2", establecimiento="0000", catalogo="9",
    tipo_existencia="01", codigo_existencia="AB-AZU-001", catalogo_internacional="", codigo_internacional="",
    fecha_documento=dt.date(2026, 10, 15), tipo_documento="00", serie_documento="VALE-SALIDA",
    numero_documento="0042", tipo_operacion="99", descripcion_existencia="AZÚCAR RUBIA",
    unidad_medida="KGM", entrada=D("0"), salida=D("-250"), estado="1", saldo_final=D("750"),
)


def campos(linea: str) -> list[str]:
    assert linea.endswith("|")
    return linea[:-1].split("|")


class TestLineaDelRegistroDeVentas:
    def test_35_campos_separados_por_pipe_y_pipe_final(self):
        linea = linea_txt(ESTRUCTURA_141, FACTURA)
        assert len(campos(linea)) == 35
        assert linea.endswith("|1|")  # campo 35 = estado, y el pipe final

    def test_linea_completa_de_una_factura(self):
        assert linea_txt(ESTRUCTURA_141, FACTURA) == (
            "20261000|V202610000001|M1|22/10/2026||01|F001|1||6|20601234565|BODEGA SAN MARTÍN & HIJOS E.I.R.L.|"
            "0.00|305.00|0.00|54.90|0.00|0.00|0.00|0.00|0.00|0.00|0.00|0.00|359.90|PEN|1.000||||||||1|"
        )

    def test_nota_de_credito_en_negativo_con_el_comprobante_que_modifica(self):
        v = campos(linea_txt(ESTRUCTURA_141, NOTA_CREDITO))
        assert (v[5], v[13], v[15], v[24]) == ("07", "-42.00", "-7.56", "-49.56")
        assert v[27:31] == ["22/10/2026", "01", "F001", "1"]

    def test_sin_cabecera_y_cada_linea_termina_en_crlf(self):
        txt = contenido_txt("140100", [FACTURA, NOTA_CREDITO])
        lineas = txt.split(FIN_DE_LINEA)
        assert lineas[-1] == "" and len(lineas) == 3
        assert lineas[0].startswith("20261000|")  # la primera línea ya es un dato, no un título

    def test_libro_sin_operaciones_es_un_archivo_vacio(self):
        assert contenido_txt("140100", []) == ""

    def test_todos_los_campos_cumplen_el_anexo_2(self):
        assert validar_filas("140100", [FACTURA, NOTA_CREDITO]) == []


class TestFormatoDeCadaValor:
    campo_importe = ESTRUCTURA_141[24]  # 25: importe total
    campo_tc = ESTRUCTURA_141[26]  # 27: tipo de cambio
    campo_texto = ESTRUCTURA_141[11]  # 12: razón social
    campo_alfa = ESTRUCTURA_121[12]  # 13: número del documento

    @pytest.mark.parametrize(("valor", "esperado"), [
        (D("1234567.5"), "1234567.50"),  # sin separador de miles, punto decimal
        (D("0.005"), "0.01"),  # redondeo comercial (ROUND_HALF_UP)
        (D("-49.56"), "-49.56"),  # negativo como "-#.##"
        (D("-0.001"), "0.00"),  # nunca "-0.00"
        (D("0"), "0.00"),
    ])
    def test_importes(self, valor, esperado):
        assert formatear(self.campo_importe, valor) == esperado

    def test_tipo_de_cambio_con_tres_decimales(self):
        assert formatear(self.campo_tc, D("3.75")) == "3.750"

    def test_fecha_dd_mm_aaaa(self):
        assert formatear(ESTRUCTURA_141[3], dt.date(2026, 1, 5)) == "05/01/2026"

    def test_campo_vacio_es_vacio_no_un_espacio(self):
        assert formatear(ESTRUCTURA_141[4], None) == ""
        assert "||||" in linea_txt(ESTRUCTURA_141, FACTURA)

    def test_texto_sin_pipe_ni_barras_y_cortado_a_su_longitud(self):
        assert formatear(self.campo_texto, "ACME | S/A \\ PERU\nSAC") == "ACME S A PERU SAC"
        assert len(formatear(self.campo_texto, "X" * 150)) == 100

    def test_alfanumerico_solo_letras_digitos_y_signos_permitidos(self):
        assert formatear(self.campo_alfa, "RECIBO Nº 12/7") == "RECIBO-No-12-7"  # NFKD: º → o


class TestReglasEntreCampos:
    def test_vencimiento_posterior_al_mes_siguiente_se_rechaza(self):
        fila = dataclasses.replace(FACTURA, fecha_vencimiento=dt.date(2027, 2, 15))
        [error] = validar_filas("140100", [fila])
        assert error.campo == 5

    def test_vencimiento_dentro_del_mes_siguiente_se_acepta(self):
        assert validar_filas("140100", [dataclasses.replace(FACTURA, fecha_vencimiento=dt.date(2026, 11, 30))]) == []

    def test_nota_sin_comprobante_modificado_se_rechaza(self):
        fila = dataclasses.replace(NOTA_CREDITO, fecha_modificado=None, tipo_modificado="")
        assert {e.campo for e in validar_filas("140100", [fila])} == {28, 29}

    def test_boleta_con_tipo_de_documento_0_se_rechaza(self):
        fila = dataclasses.replace(FACTURA, tipo_comprobante="03", serie="B001", tipo_documento_cliente="0",
                                   numero_documento_cliente="00000000")
        assert [e.campo for e in validar_filas("140100", [fila])] == [10]

    def test_cuo_con_ampersand_se_rechaza(self):
        assert [e.campo for e in validar_filas("140100", [dataclasses.replace(FACTURA, cuo="V&1")])] == [2]

    def test_un_libro_invalido_no_se_genera(self):
        fila = dataclasses.replace(FACTURA, estado="")
        with pytest.raises(EstructuraPleInvalida) as error:
            contenido_txt("140100", [fila])
        assert error.value.codigo == "ERR-PLE-ESTRUCTURA"
        assert "campo 35" in error.value.mensaje


class TestContraejemplosDelTxt:
    """Lo que el programa PLE rechazaría: se detecta antes de entregar el archivo."""

    def test_estructura_de_36_columnas_no_es_la_del_anexo_2(self):
        # Partir el campo 30 en "serie" y "dependencia aduanera" produce 36 columnas y corre
        # desde el 31 en adelante el número modificado, el contrato, el error y el estado.
        valores = campos(linea_txt(ESTRUCTURA_141, FACTURA))
        con_36 = "|".join([*valores[:30], "", *valores[30:]]) + "|"
        [error] = validar_linea(ESTRUCTURA_141, con_36)
        assert "36 campos" in error.motivo

    def test_linea_sin_pipe_final(self):
        [error] = validar_linea(ESTRUCTURA_141, linea_txt(ESTRUCTURA_141, FACTURA)[:-1])
        assert "separador" in error.motivo

    @pytest.mark.parametrize(("indice", "valor", "motivo"), [
        (24, "1,359.90", "formato"),  # separador de miles
        (24, "359.9", "formato"),  # un solo decimal
        (3, "2026-10-22", "formato"),  # fecha ISO en lugar de DD/MM/AAAA
        (3, "31/09/2026", "fecha válida"),
        (26, "3.75", "formato"),  # tipo de cambio con 2 decimales
        (0, "20261300", "regla"),  # mes 13
        (2, "X1", "regla"),  # el asiento empieza con A, M o C
        (34, "", "obligatorio"),
        (10, "2060123456512345", "longitud"),
    ])
    def test_campo_mal_formado(self, indice, valor, motivo):
        valores = campos(linea_txt(ESTRUCTURA_141, FACTURA))
        valores[indice] = valor
        [error] = validar_linea(ESTRUCTURA_141, "|".join(valores) + "|")
        assert (error.campo, motivo in error.motivo) == (indice + 1, True)


class TestLineaDelInventario121:
    def test_19_campos_y_salida_en_negativo(self):
        v = campos(linea_txt(ESTRUCTURA_121, SALIDA))
        assert len(v) == 19
        assert v[7:9] == ["", ""]  # 8 y 9: catálogo internacional, opcional
        assert (v[9], v[10], v[11], v[12]) == ("15/10/2026", "00", "VALE-SALIDA", "0042")
        assert (v[16], v[17], v[18]) == ("0.00", "-250.00", "1")

    def test_el_saldo_no_va_en_el_txt(self):
        assert "750.00" not in linea_txt(ESTRUCTURA_121, SALIDA)

    def test_entrada_y_salida_son_excluyentes(self):
        fila = dataclasses.replace(SALIDA, entrada=D("10"))
        assert [e.campo for e in validar_filas("120100", [fila])] == [18]

    def test_documento_sin_serie_se_rechaza(self):
        assert [e.campo for e in validar_filas("120100", [dataclasses.replace(SALIDA, serie_documento="")])] == [12]

    def test_venta_con_documento_interno_se_rechaza(self):
        # Error que devolvió el PLE 5.2.0.7 (filas 2, 6, 13 y 14, columna 11) con la versión anterior.
        fila = dataclasses.replace(SALIDA, tipo_operacion="01")
        [error] = validar_filas("120100", [fila])
        assert (error.campo, "tipo de operación" in error.motivo) == (11, True)

    def test_unidad_con_codigo_numerico_de_la_tabla_6_anterior_se_rechaza(self):
        # Error que devolvió el PLE 5.2.0.7 en las 23 filas (columna 16) con la versión anterior.
        [error] = validar_filas("120100", [dataclasses.replace(SALIDA, unidad_medida="01")])
        assert error.campo == 16

    def test_venta_con_factura_se_acepta(self):
        fila = dataclasses.replace(SALIDA, tipo_operacion="01", tipo_documento="01", serie_documento="F001",
                                   numero_documento="1")
        assert validar_filas("120100", [fila]) == []

    def test_establecimiento_de_menos_de_4_digitos_se_rechaza(self):
        assert [e.campo for e in validar_filas("120100", [dataclasses.replace(SALIDA, establecimiento="1")])] == [4]
