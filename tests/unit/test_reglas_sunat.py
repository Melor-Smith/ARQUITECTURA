"""tests/unit/test_reglas_sunat.py

Pruebas unitarias para el motor tributario y de reglas normativas SUNAT (UBL 2.1).
Valida Catálogo 08 de ISC, Catálogo 06 (RUC), cálculo de IGV y generación de XML UBL.
"""

import pytest
from src.services.sunat_ubl_service import SunatUBLService
from tests.mocks.mock_db import (
    CATALOGO_08_ISC_SUNAT,
    MOCK_FACTURA_VALIDA,
    MOCK_MIGRACION_VALIDA,
)


class TestReglasValidacionSUNAT:
    """Conjunto de pruebas para la validación de reglas SUNAT y Catálogos oficiales."""

    def test_validar_ruc_exitoso_empresa(self):
        """RUC de persona jurídica (prefijo 20 y 11 dígitos) debe ser válido."""
        assert SunatUBLService.validar_ruc("20556677889") is True

    def test_validar_ruc_exitoso_persona_natural(self):
        """RUC de persona natural con negocio (prefijo 10 y 11 dígitos) debe ser válido."""
        assert SunatUBLService.validar_ruc("10445566771") is True

    def test_validar_ruc_longitud_erronea(self):
        """RUC con longitud distinta a 11 dígitos debe lanzar ValueError."""
        with pytest.raises(ValueError, match="11 dígitos"):
            SunatUBLService.validar_ruc("2055667788")  # 10 dígitos

        with pytest.raises(ValueError, match="11 dígitos"):
            SunatUBLService.validar_ruc("205566778899")  # 12 dígitos

    def test_validar_ruc_prefijo_invalido(self):
        """RUC que no inicie con 10 o 20 debe ser rechazado conforme al Catálogo 06."""
        with pytest.raises(ValueError, match="iniciar con 10 o 20"):
            SunatUBLService.validar_ruc("30556677889")

    def test_catalogo_08_isc_codigos_validos(self):
        """Los códigos '01', '02' y '03' del Catálogo 08 deben ser admitidos."""
        for codigo in ["01", "02", "03"]:
            descripcion = SunatUBLService.validar_codigo_isc(codigo)
            assert descripcion == CATALOGO_08_ISC_SUNAT[codigo]

    def test_catalogo_08_isc_codigo_invalido(self):
        """Un código no registrado en el Catálogo 08 debe ser rechazado."""
        with pytest.raises(ValueError, match="Catálogo 08"):
            SunatUBLService.validar_codigo_isc("99")

        with pytest.raises(ValueError, match="Catálogo 08"):
            SunatUBLService.validar_codigo_isc("00")

    def test_calcular_igv_18_porciento(self):
        """Verifica que para operaciones gravadas (código 10), el IGV sea exactamente el 18%."""
        base_gravada = 200.00
        igv_calculado = SunatUBLService.calcular_igv(base_gravada, afectacion_codigo="10")
        assert igv_calculado == 36.00

    def test_generar_hash_cpe_deterministico(self):
        """El resumen SHA-256 debe generar un hash válido con prefijo sha256-."""
        xml_dummy = "<Invoice><cbc:ID>F001-000001</cbc:ID></Invoice>"
        hash_res = SunatUBLService.generar_hash_cpe(xml_dummy)
        assert hash_res.startswith("sha256-")
        assert len(hash_res) == 7 + 64  # 'sha256-' + 64 caracteres hex

    def test_generacion_xml_ubl_2_1_completo(self):
        """La generación del XML debe estructurarse conforme a OASIS UBL-Invoice-2.1.xsd."""
        xml = SunatUBLService.construir_xml_ubl_2_1(MOCK_FACTURA_VALIDA)
        assert "<Invoice xmlns=" in xml
        assert "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>" in xml
        assert "<cbc:CustomizationID>2.0</cbc:CustomizationID>" in xml
        assert "<cbc:ID>F001-000001</cbc:ID>" in xml
        assert "cac:AccountingSupplierParty" in xml
        assert "cac:AccountingCustomerParty" in xml
        assert "cac:TaxTotal" in xml
        assert "cac:LegalMonetaryTotal" in xml

    def test_clasificar_ficha_legado_salida(self):
        """Una ficha con salida > 0 y ingreso == 0 debe tipificarse como SALIDA_POR_FACTURAR."""
        movimiento = SunatUBLService.clasificar_movimiento_legado(ingreso=0, salida=5)
        assert movimiento == "SALIDA_POR_FACTURAR"

    def test_clasificar_ficha_legado_ingreso(self):
        """Una ficha con ingreso > 0 y salida == 0 debe tipificarse como INGRESO_ALMACEN."""
        movimiento = SunatUBLService.clasificar_movimiento_legado(ingreso=15, salida=0)
        assert movimiento == "INGRESO_ALMACEN"

    def test_clasificar_ficha_legado_invalida_sin_movimiento(self):
        """Una ficha con ingreso == 0 y salida == 0 no es válida para trazabilidad."""
        with pytest.raises(ValueError, match="movimiento cuantificable"):
            SunatUBLService.clasificar_movimiento_legado(ingreso=0, salida=0)
