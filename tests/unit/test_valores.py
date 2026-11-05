"""Objetos de valor: RUC (módulo 11), documento de identidad, serie y correlativo."""

import pytest

from src.domain.catalogos import TipoDocumentoIdentidad
from src.domain.errores import CorrelativoInvalido, DocumentoIdentidadInvalido, RucInvalido, SerieInvalida
from src.domain.valores import (
    Correlativo,
    DocumentoIdentidad,
    NumeroComprobante,
    Ruc,
    Serie,
    digito_verificador_ruc,
)


def ruc_valido(primeros_diez: str) -> str:
    return primeros_diez + str(digito_verificador_ruc(primeros_diez))


class TestRuc:
    @pytest.mark.parametrize("prefijo", ["10", "15", "16", "17", "20"])
    def test_acepta_todos_los_prefijos_sunat(self, prefijo):
        assert str(Ruc(ruc_valido(prefijo + "12345678")))

    def test_rechaza_el_ruc_con_digito_verificador_incorrecto_que_el_sistema_anterior_aceptaba(self):
        with pytest.raises(RucInvalido, match="módulo 11"):
            Ruc("20123456780")

    def test_acepta_el_mismo_ruc_con_su_digito_correcto(self):
        assert Ruc("20123456786").valor == "20123456786"

    @pytest.mark.parametrize("valor", ["2055667788", "205566778841", "2055667788A", ""])
    def test_rechaza_longitud_o_caracteres_invalidos(self, valor):
        with pytest.raises(RucInvalido, match="11 dígitos"):
            Ruc(valor)

    @pytest.mark.parametrize("prefijo", ["11", "30", "99"])
    def test_rechaza_prefijos_no_sunat(self, prefijo):
        with pytest.raises(RucInvalido, match="debe iniciar"):
            Ruc(ruc_valido(prefijo + "12345678"))


class TestDocumentoIdentidad:
    def test_dni_de_8_digitos(self):
        assert DocumentoIdentidad(TipoDocumentoIdentidad.DNI, "46027897").numero == "46027897"

    def test_dni_con_otra_longitud(self):
        with pytest.raises(DocumentoIdentidadInvalido):
            DocumentoIdentidad(TipoDocumentoIdentidad.DNI, "4602789")

    def test_tipo_ruc_aplica_modulo_11(self):
        with pytest.raises(RucInvalido):
            DocumentoIdentidad(TipoDocumentoIdentidad.RUC, "20123456780")


class TestSerie:
    @pytest.mark.parametrize("valor", ["F001", "B001", "FA01", "BZ99", "FC01"])
    def test_series_validas_incluidas_alfanumericas(self, valor):
        assert Serie(valor).valor == valor

    @pytest.mark.parametrize("valor", ["X001", "F01", "F0001", "f001", "F-01"])
    def test_series_invalidas(self, valor):
        with pytest.raises(SerieInvalida):
            Serie(valor)


class TestCorrelativo:
    @pytest.mark.parametrize("valor", [1, 42, 99_999_999])
    def test_rango_legal(self, valor):
        assert Correlativo(valor).valor == valor

    @pytest.mark.parametrize("valor", [0, -1, 100_000_000])
    def test_fuera_de_rango(self, valor):
        with pytest.raises(CorrelativoInvalido):
            Correlativo(valor)

    def test_no_acepta_texto(self):
        with pytest.raises(CorrelativoInvalido):
            Correlativo("1")  # type: ignore[arg-type]


class TestNumeroComprobante:
    def test_correlativo_de_8_digitos(self):
        numero = NumeroComprobante.parsear("F001-12345678")
        assert numero.correlativo.valor == 12_345_678
        assert str(numero) == "F001-12345678"

    def test_ceros_a_la_izquierda_representan_el_mismo_numero(self):
        assert NumeroComprobante.parsear("F001-00000001") == NumeroComprobante.parsear("F001-1")

    def test_serie_y_correlativo_solo_se_unen_al_serializar(self):
        numero = NumeroComprobante(Serie("FA01"), Correlativo(7))
        assert (numero.serie.valor, numero.correlativo.valor, str(numero)) == ("FA01", 7, "FA01-7")

    @pytest.mark.parametrize("texto", ["F001-123456789", "F001", "F001-", "X001-1"])
    def test_formatos_invalidos(self, texto):
        with pytest.raises(SerieInvalida):
            NumeroComprobante.parsear(texto)
