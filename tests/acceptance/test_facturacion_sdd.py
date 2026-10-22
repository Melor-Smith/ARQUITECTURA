"""tests/acceptance/test_facturacion_sdd.py

Tests de aceptación extremo a extremo (SDD) sobre los endpoints de FastAPI.
Verifican el cumplimiento del contrato specs/contracts/ubl-invoice-api.yaml.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from tests.mocks.mock_db import (
    MOCK_FACTURA_VALIDA,
    MOCK_MIGRACION_VALIDA,
    reiniciar,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_teardown():
    reiniciar()
    yield
    reiniciar()


class TestEmisionFacturaUBL:
    """Pruebas de aceptación para el endpoint POST /api/v1/facturas."""

    def test_emision_factura_valida_201(self):
        """Escenario: Emisión exitosa de factura con UBL 2.1 y Catálogo 8 SUNAT."""
        response = client.post("/api/v1/facturas", json=MOCK_FACTURA_VALIDA)
        assert response.status_code == 201
        data = response.json()
        assert data["id_comprobante"] == "F001-000001"
        assert data["estado_sunat"] == "ACEPTADO"
        assert data["hash_cpe"].startswith("sha256-")
        assert "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>" in data["xml_ubl_generado"]
        assert "cac:AccountingSupplierParty" in data["xml_ubl_generado"]
        assert "cac:AccountingCustomerParty" in data["xml_ubl_generado"]
        assert "F001-000001" in data["mensaje_ose"]

    def test_emision_factura_ruc_invalido_400(self):
        """Escenario: Rechazo de factura por RUC de comprador que no cumple 11 dígitos o formato."""
        payload = dict(MOCK_FACTURA_VALIDA)
        payload["comprador"] = dict(payload["comprador"])
        payload["comprador"]["ruc"] = "12345"  # Inválido: no tiene 11 dígitos

        response = client.post("/api/v1/facturas", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "codigo" in data
        assert "ERR-SUNAT-RUC" in data["codigo"] or "RUC" in data["mensaje"]

    def test_emision_factura_catalogo08_isc_invalido_400(self):
        """Escenario: Rechazo de factura por código de sistema de ISC inválido según Catálogo 08."""
        payload = dict(MOCK_FACTURA_VALIDA)
        items_modificados = [dict(payload["items"][0])]
        items_modificados[0]["codigo_sistema_isc"] = "99"  # No existe en Catálogo 08
        payload["items"] = items_modificados

        response = client.post("/api/v1/facturas", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "codigo" in data
        assert "CAT08" in data["codigo"] or "ISC" in data["mensaje"]


class TestConsultaFacturaUBL:
    """Pruebas de aceptación para el endpoint GET /api/v1/facturas/{id_comprobante}."""

    def test_consultar_factura_existente_200(self):
        """Escenario: Consulta exitosa de comprobante previamente emitido."""
        # 1. Emitir comprobante
        post_resp = client.post("/api/v1/facturas", json=MOCK_FACTURA_VALIDA)
        assert post_resp.status_code == 201

        # 2. Consultar comprobante
        get_resp = client.get("/api/v1/facturas/F001-000001")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id_comprobante"] == "F001-000001"
        assert data["estado_sunat"] == "ACEPTADO"
        assert len(data["hash_cpe"]) > 10
        assert "<Invoice" in data["xml_ubl_generado"]

    def test_consultar_factura_inexistente_404(self):
        """Escenario: Consulta de comprobante que no existe en el sistema."""
        response = client.get("/api/v1/facturas/F999-999999")
        assert response.status_code == 404
        data = response.json()
        assert "codigo" in data
        assert "ERR-NOT-FOUND" in data["codigo"] or "no encontrado" in data["mensaje"].lower()


class TestMigracionFichasLegado:
    """Pruebas de aceptación para el endpoint POST /api/v1/migracion/fichas-legado."""

    def test_migracion_ficha_legado_salida_201(self):
        """Escenario: Migración de vale de salida del almacén legado a entidad formal UBL."""
        response = client.post("/api/v1/migracion/fichas-legado", json=MOCK_MIGRACION_VALIDA)
        assert response.status_code == 201
        data = response.json()
        assert data["id_migracion"].startswith("MIG-")
        assert data["nro_documento_legado"] == "VALE-SALIDA-0042"
        assert data["tipo_movimiento"] == "SALIDA_POR_FACTURAR"
        assert data["estado_trazabilidad"] == "MIGRADO_CON_TRAZABILIDAD"
        assert data["serie_ubl_sugerida"].startswith("F001-")

    def test_migracion_ficha_legado_ingreso_201(self):
        """Escenario: Migración de guía interna de reposición con movimiento de ingreso."""
        payload = {
            "fecha": "2026-10-16",
            "ingreso": 20,
            "salida": 0,
            "producto": "Saco de Arroz Extra 50kg",
            "nro_documento": "GUIA-INT-0015",
        }
        response = client.post("/api/v1/migracion/fichas-legado", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["tipo_movimiento"] == "INGRESO_ALMACEN"
        assert data["estado_trazabilidad"] == "MIGRADO_CON_TRAZABILIDAD"

    def test_migracion_ficha_legado_invalida_400(self):
        """Escenario: Rechazo de ficha informal sin movimiento cuantificable."""
        payload = {
            "fecha": "2026-10-16",
            "ingreso": 0,
            "salida": 0,
            "producto": "Producto Fantasma",
            "nro_documento": "VALE-VACIO-0000",
        }
        response = client.post("/api/v1/migracion/fichas-legado", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "codigo" in data
