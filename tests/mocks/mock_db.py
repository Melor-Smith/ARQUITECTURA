"""tests/mocks/mock_db.py

Banco de datos en memoria y mocks oficiales para Spec-Driven Development.
Única fuente autorizada de datos de prueba según las Reglas Duras del proyecto.
"""

from copy import deepcopy
from typing import Any, Dict, List

# Catálogos oficiales SUNAT (RS N° 097-2012 y modificatorias)
CATALOGO_01_TIPO_DOCUMENTO = {
    "01": "Factura",
    "03": "Boleta de Venta",
    "07": "Nota de Crédito",
    "08": "Nota de Débito",
}

CATALOGO_02_MONEDAS = {
    "PEN": "Soles",
    "USD": "Dólares Americanos",
    "EUR": "Euros",
}

CATALOGO_06_TIPO_DOC_IDENTIDAD = {
    "0": "Doc.trib.no.dom.sin.ruc",
    "1": "DNI",
    "4": "Carnet de extranjería",
    "6": "RUC",
    "7": "Pasaporte",
    "A": "Cédula diplomática",
}

CATALOGO_07_AFECTACION_IGV = {
    "10": "Gravado - Operación Onerosa",
    "11": "Gravado – Retiro por premio",
    "20": "Exonerado - Operación Onerosa",
    "30": "Inafecto - Operación Onerosa",
    "40": "Exportación",
}

# Obligatorio: Catálogo 08 de SUNAT - Tipos de Sistema de Cálculo del ISC
CATALOGO_08_ISC_SUNAT = {
    "01": "Sistema al valor",
    "02": "Aplicación del Monto Fijo",
    "03": "Sistema de Precios de Venta al Público",
}

# Fichas históricas informales del software legado de almacén de ABC Software Corp
DB_FICHAS_LEGADO_INICIAL: List[Dict[str, Any]] = [
    {
        "fecha": "2026-10-15",
        "ingreso": 0,
        "salida": 5,
        "producto": "Saco de Azúcar Rubia 50kg",
        "nro_documento": "VALE-SALIDA-0042",
    },
    {
        "fecha": "2026-10-16",
        "ingreso": 20,
        "salida": 0,
        "producto": "Saco de Arroz Extra 50kg",
        "nro_documento": "GUIA-INT-0015",
    },
    {
        "fecha": "2026-10-17",
        "ingreso": 0,
        "salida": 2,
        "producto": "Caja Aceite Vegetal 12x1L",
        "nro_documento": "VALE-SALIDA-0099",
    },
]

# Copia mutable en memoria
DB_FICHAS_LEGADO: List[Dict[str, Any]] = deepcopy(DB_FICHAS_LEGADO_INICIAL)

# Almacenes en memoria para Comprobantes y Fichas Migradas
DB_FACTURAS: Dict[str, Dict[str, Any]] = {}
DB_MIGRACIONES: Dict[str, Dict[str, Any]] = {}

# Mocks conformes 100% con los schemas OpenAPI (specs/contracts/ubl-invoice-api.yaml)
MOCK_FACTURA_VALIDA: Dict[str, Any] = {
    "ubl_version": "2.1",
    "tipo_documento_codigo": "01",
    "serie_correlativo": "F001-000001",
    "fecha_emision": "2026-10-22",
    "codigo_moneda": "PEN",
    "nro_documento_legado_origen": "VALE-SALIDA-0042",
    "vendedor": {
        "codigo_tipo_documento": "6",
        "ruc": "20556677889",
        "razon_social": "ABC SOFTWARE CORP S.A.C.",
        "ubigeo": "150101",
        "direccion": "AV. INDUSTRIAL 450 - LIMA",
    },
    "comprador": {
        "codigo_tipo_documento": "6",
        "ruc": "20123456789",
        "razon_social": "DISTRIBUIDORA NORTE S.A.C.",
        "ubigeo": "150101",
        "direccion": "JR. COMERCIO 123 - LIMA",
    },
    "items": [
        {
            "codigo_producto": "AB-001",
            "descripcion": "Saco de Arroz Extra 50kg",
            "cantidad": 2,
            "valor_unitario": 100.00,
            "codigo_afectacion_igv": "10",
            "codigo_sistema_isc": "01",
            "isc_item": 0.00,
            "igv_item": 36.00,
            "icbper_item": 0.00,
        }
    ],
    "totales": {
        "total_gravadas": 200.00,
        "total_igv": 36.00,
        "total_isc": 0.00,
        "total_icbper": 0.00,
        "importe_total": 236.00,
    },
}

MOCK_MIGRACION_VALIDA: Dict[str, Any] = {
    "fecha": "2026-10-15",
    "ingreso": 0,
    "salida": 5,
    "producto": "Saco de Azúcar Rubia 50kg",
    "nro_documento": "VALE-SALIDA-0042",
}

MOCK_RESPUESTA_EXITO: Dict[str, Any] = {
    "id_comprobante": "F001-000001",
    "estado_sunat": "ACEPTADO",
    "hash_cpe": "sha256-4a8b9c1d2e3f",
    "xml_ubl_generado": (
        "<Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'>"
        "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>"
        "<cbc:CustomizationID>2.0</cbc:CustomizationID>"
        "<cbc:ID>F001-000001</cbc:ID>"
        "<cbc:IssueDate>2026-10-22</cbc:IssueDate>"
        "<cbc:DocumentCurrencyCode>PEN</cbc:DocumentCurrencyCode>"
        "<cac:AccountingSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID='6'>20556677889</cbc:ID></cac:PartyIdentification><cac:PartyLegalEntity><cbc:RegistrationName>ABC SOFTWARE CORP S.A.C.</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>"
        "<cac:AccountingCustomerParty><cac:Party><cac:PartyIdentification><cbc:ID schemeID='6'>20123456789</cbc:ID></cac:PartyIdentification><cac:PartyLegalEntity><cbc:RegistrationName>DISTRIBUIDORA NORTE S.A.C.</cbc:RegistrationName></cac:PartyLegalEntity></cac:Party></cac:AccountingCustomerParty>"
        "<cac:TaxTotal><cbc:TaxAmount currencyID='PEN'>36.00</cbc:TaxAmount></cac:TaxTotal>"
        "<cac:LegalMonetaryTotal><cbc:PayableAmount currencyID='PEN'>236.00</cbc:PayableAmount></cac:LegalMonetaryTotal>"
        "</Invoice>"
    ),
    "mensaje_ose": "La Factura F001-000001 cumple con UBL-Invoice-2.1.xsd y ha sido ACEPTADA.",
}


def reiniciar() -> None:
    """Restablece el estado de los almacenes en memoria para garantizar aislamiento de tests."""
    global DB_FICHAS_LEGADO, DB_FACTURAS, DB_MIGRACIONES
    DB_FICHAS_LEGADO = deepcopy(DB_FICHAS_LEGADO_INICIAL)
    DB_FACTURAS.clear()
    DB_MIGRACIONES.clear()
