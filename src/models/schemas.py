"""src/models/schemas.py

Modelos de Dominio y Contratos DTO implementados con Pydantic v2.
Correspondencia 1:1 exacta con specs/contracts/ubl-invoice-api.yaml.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
import re


class ActorParty(BaseModel):
    """Mapea cac:AccountingSupplierParty y cac:AccountingCustomerParty en UBL 2.1."""
    codigo_tipo_documento: Literal["6"] = Field(
        default="6",
        description="Catálogo 06 SUNAT (6 = RUC)"
    )
    ruc: str = Field(
        ...,
        description="RUC de 11 dígitos iniciando con 10 o 20",
        examples=["20556677889"]
    )
    razon_social: str = Field(..., examples=["ABC SOFTWARE CORP S.A.C."])
    ubigeo: str = Field(..., examples=["150101"])
    direccion: str = Field(..., examples=["AV. INDUSTRIAL 450 - LIMA"])

    @field_validator("ruc")
    @classmethod
    def validar_formato_ruc(cls, v: str) -> str:
        if not re.match(r"^(10|20)\d{9}$", v):
            raise ValueError("El RUC debe tener 11 dígitos numéricos y comenzar con 10 o 20 (Catálogo 06 SUNAT)")
        return v


class ItemFactura(BaseModel):
    """Mapea cac:InvoiceLine en UBL-Invoice-2.1.xsd."""
    codigo_producto: str = Field(..., examples=["AB-001"])
    descripcion: str = Field(..., examples=["Saco de Arroz Extra 50kg"])
    cantidad: float = Field(..., gt=0, examples=[2.0])
    valor_unitario: float = Field(..., ge=0, examples=[100.00])
    codigo_afectacion_igv: str = Field(
        default="10",
        description="Catálogo 07 SUNAT (10 = Gravado - Operación Onerosa)",
        examples=["10"]
    )
    codigo_sistema_isc: Optional[Literal["01", "02", "03"]] = Field(
        default=None,
        description="Catálogo 08 SUNAT: 01 Al valor, 02 Monto fijo, 03 Precios venta público",
        examples=["01"]
    )
    isc_item: float = Field(default=0.00, ge=0, examples=[0.00])
    igv_item: float = Field(..., ge=0, examples=[36.00])
    icbper_item: float = Field(default=0.00, ge=0, examples=[0.00])


class ImpuestosTotales(BaseModel):
    """Mapea cac:TaxTotal y cac:LegalMonetaryTotal en UBL 2.1."""
    total_gravadas: float = Field(..., ge=0, examples=[200.00])
    total_igv: float = Field(..., ge=0, examples=[36.00])
    total_isc: float = Field(default=0.00, ge=0, examples=[0.00])
    total_icbper: float = Field(default=0.00, ge=0, examples=[0.00])
    importe_total: float = Field(..., ge=0, examples=[236.00])


class FacturaRequest(BaseModel):
    """Contrato de entrada para emisión de comprobante UBL 2.1."""
    ubl_version: str = Field(default="2.1", examples=["2.1"])
    tipo_documento_codigo: Literal["01"] = Field(
        default="01",
        description="Catálogo 01 SUNAT (01 = Factura)",
        examples=["01"]
    )
    serie_correlativo: str = Field(
        ...,
        pattern=r"^F\d{3}-\d{6}$",
        examples=["F001-000001"]
    )
    fecha_emision: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        examples=["2026-10-22"]
    )
    codigo_moneda: Literal["PEN", "USD"] = Field(
        default="PEN",
        description="Catálogo 02 SUNAT (PEN, USD)",
        examples=["PEN"]
    )
    nro_documento_legado_origen: Optional[str] = Field(
        default=None,
        description="Trazabilidad opcional hacia la ficha del software básico legado",
        examples=["DOC-INT-9981"]
    )
    vendedor: ActorParty
    comprador: ActorParty
    items: List[ItemFactura] = Field(..., min_length=1)
    totales: ImpuestosTotales


class FacturaResponse(BaseModel):
    """Contrato de salida tras emisión aceptada por OSE/SUNAT."""
    id_comprobante: str = Field(..., examples=["F001-000001"])
    estado_sunat: Literal["ACEPTADO", "RECHAZADO"] = Field(default="ACEPTADO", examples=["ACEPTADO"])
    hash_cpe: str = Field(..., examples=["sha256-4a8b9c1d2e3f"])
    xml_ubl_generado: str = Field(..., examples=["<Invoice>...</Invoice>"])
    mensaje_ose: str = Field(..., examples=["La Factura F001-000001 cumple con UBL-Invoice-2.1.xsd y ha sido ACEPTADA."])


class FichaLegadoRequest(BaseModel):
    """Estructura histórica del software básico de almacén."""
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["2026-10-15"])
    ingreso: float = Field(..., ge=0, examples=[0.0])
    salida: float = Field(..., ge=0, examples=[5.0])
    producto: str = Field(..., min_length=1, examples=["Saco de Azúcar Rubia 50kg"])
    nro_documento: str = Field(..., min_length=1, examples=["VALE-SALIDA-0042"])


class FichaMigradaResponse(BaseModel):
    """Respuesta tras migración exitosa con trazabilidad."""
    id_migracion: str = Field(..., examples=["MIG-2026-0001"])
    nro_documento_legado: str = Field(..., examples=["VALE-SALIDA-0042"])
    tipo_movimiento: Literal["INGRESO_ALMACEN", "SALIDA_POR_FACTURAR"] = Field(
        ...,
        examples=["SALIDA_POR_FACTURAR"]
    )
    estado_trazabilidad: str = Field(
        default="MIGRADO_CON_TRAZABILIDAD",
        examples=["MIGRADO_CON_TRAZABILIDAD"]
    )
    serie_ubl_sugerida: str = Field(..., examples=["F001-000002"])


class ErrorResponse(BaseModel):
    """Contrato de error estandarizado."""
    codigo: str = Field(..., examples=["ERR-SUNAT-CAT08"])
    mensaje: str = Field(..., examples=["Incumplimiento de regla normativa SUNAT o esquema UBL-Invoice-2.1.xsd"])
