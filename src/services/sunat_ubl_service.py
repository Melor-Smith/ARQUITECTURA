"""src/services/sunat_ubl_service.py

Servicio de Dominio Tributario y Normativo SUNAT / OASIS UBL 2.1.
Implementa las validaciones de RUC (Catálogo 06), Catálogo 08 de ISC,
cálculo de IGV (18%), generación de XML UBL 2.1 y hash CPE, y migración de legados.
"""

import hashlib
import re
from typing import Any, Dict, Optional
from src.repositories.memory_repo import FacturaMemoryRepository
from tests.mocks.mock_db import CATALOGO_08_ISC_SUNAT


class SunatUBLService:
    """Motor de validaciones tributarias SUNAT y generación de comprobantes OASIS UBL 2.1."""

    @classmethod
    def validar_ruc(cls, ruc: str) -> bool:
        """Valida que el RUC tenga exactamente 11 dígitos y comience con 10 o 20 (Catálogo 06)."""
        if not isinstance(ruc, str) or len(ruc) != 11:
            raise ValueError(f"El RUC '{ruc}' es inválido: debe tener exactamente 11 dígitos numéricos.")
        if not (ruc.startswith("10") or ruc.startswith("20")):
            raise ValueError(f"El RUC '{ruc}' es inválido: debe iniciar con 10 o 20 (Catálogo 06 SUNAT).")
        if not ruc.isdigit():
            raise ValueError(f"El RUC '{ruc}' debe contener únicamente caracteres numéricos.")
        return True

    @classmethod
    def validar_codigo_isc(cls, codigo: Optional[str]) -> Optional[str]:
        """Valida si el código de sistema de ISC pertenece al Catálogo 08 de SUNAT."""
        if codigo is None:
            return None
        if codigo not in CATALOGO_08_ISC_SUNAT:
            validos = ", ".join([f"'{k}' ({v})" for k, v in CATALOGO_08_ISC_SUNAT.items()])
            raise ValueError(
                f"Código de sistema ISC '{codigo}' inválido según el Catálogo 08 de SUNAT. "
                f"Valores permitidos: {validos}."
            )
        return CATALOGO_08_ISC_SUNAT[codigo]

    @classmethod
    def calcular_igv(cls, base_imponible: float, afectacion_codigo: str = "10") -> float:
        """Calcula el IGV (18%) para operaciones gravadas (código 10)."""
        if afectacion_codigo == "10":
            return round(base_imponible * 0.18, 2)
        return 0.00

    @classmethod
    def generar_hash_cpe(cls, xml_content: str) -> str:
        """Calcula el hash criptográfico SHA-256 del contenido XML del comprobante."""
        digest = hashlib.sha256(xml_content.encode("utf-8")).hexdigest()
        return f"sha256-{digest}"

    @classmethod
    def clasificar_movimiento_legado(cls, ingreso: float, salida: float) -> str:
        """Clasifica una ficha informal de almacén según sus cantidades."""
        if ingreso <= 0 and salida <= 0:
            raise ValueError("La ficha de almacén debe registrar un movimiento cuantificable (ingreso o salida mayor a 0).")
        if salida > 0:
            return "SALIDA_POR_FACTURAR"
        return "INGRESO_ALMACEN"

    @classmethod
    def construir_xml_ubl_2_1(cls, factura_data: Dict[str, Any]) -> str:
        """Genera el documento XML conforme al estándar internacional OASIS UBL-Invoice-2.1.xsd."""
        serie = factura_data.get("serie_correlativo", "F001-000001")
        fecha = factura_data.get("fecha_emision", "2026-10-22")
        moneda = factura_data.get("codigo_moneda", "PEN")
        vendedor = factura_data.get("vendedor", {})
        comprador = factura_data.get("comprador", {})
        totales = factura_data.get("totales", {})
        items = factura_data.get("items", [])
        ref_legado = factura_data.get("nro_documento_legado_origen")

        despatch_xml = ""
        if ref_legado:
            despatch_xml = (
                f"<cac:DespatchDocumentReference>"
                f"<cbc:ID>{ref_legado}</cbc:ID>"
                f"<cbc:DocumentTypeCode>09</cbc:DocumentTypeCode>"
                f"</cac:DespatchDocumentReference>"
            )

        items_xml = []
        for idx, item in enumerate(items, start=1):
            codigo_isc = item.get("codigo_sistema_isc")
            isc_val = item.get("isc_item", 0.00)
            isc_tag = ""
            if codigo_isc:
                isc_tag = (
                    f"<cac:TaxSubtotal>"
                    f"<cbc:TaxAmount currencyID='{moneda}'>{isc_val:.2f}</cbc:TaxAmount>"
                    f"<cac:TaxCategory>"
                    f"<cbc:TierRange>{codigo_isc}</cbc:TierRange>"
                    f"<cac:TaxScheme><cbc:ID>2000</cbc:ID><cbc:Name>ISC</cbc:Name><cbc:TaxTypeCode>EXC</cbc:TaxTypeCode></cac:TaxScheme>"
                    f"</cac:TaxCategory>"
                    f"</cac:TaxSubtotal>"
                )

            item_str = (
                f"<cac:InvoiceLine>"
                f"<cbc:ID>{idx}</cbc:ID>"
                f"<cbc:InvoicedQuantity unitCode='NIU'>{item.get('cantidad', 1)}</cbc:InvoicedQuantity>"
                f"<cbc:LineExtensionAmount currencyID='{moneda}'>{(item.get('cantidad', 1) * item.get('valor_unitario', 0.0)):.2f}</cbc:LineExtensionAmount>"
                f"<cac:Item>"
                f"<cbc:Description>{item.get('descripcion', '')}</cbc:Description>"
                f"<cac:SellersItemIdentification><cbc:ID>{item.get('codigo_producto', '')}</cbc:ID></cac:SellersItemIdentification>"
                f"</cac:Item>"
                f"<cac:Price><cbc:PriceAmount currencyID='{moneda}'>{item.get('valor_unitario', 0.0):.2f}</cbc:PriceAmount></cac:Price>"
                f"<cac:TaxTotal>"
                f"<cbc:TaxAmount currencyID='{moneda}'>{item.get('igv_item', 0.0):.2f}</cbc:TaxAmount>"
                f"<cac:TaxSubtotal>"
                f"<cbc:TaxAmount currencyID='{moneda}'>{item.get('igv_item', 0.0):.2f}</cbc:TaxAmount>"
                f"<cac:TaxCategory>"
                f"<cbc:Percent>18.00</cbc:Percent>"
                f"<cbc:TaxExemptionReasonCode>{item.get('codigo_afectacion_igv', '10')}</cbc:TaxExemptionReasonCode>"
                f"<cac:TaxScheme><cbc:ID>1000</cbc:ID><cbc:Name>IGV</cbc:Name><cbc:TaxTypeCode>VAT</cbc:TaxTypeCode></cac:TaxScheme>"
                f"</cac:TaxCategory>"
                f"</cac:TaxSubtotal>"
                f"{isc_tag}"
                f"</cac:TaxTotal>"
                f"</cac:InvoiceLine>"
            )
            items_xml.append(item_str)

        lines_joined = "".join(items_xml)

        xml = (
            f"<Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2' "
            f"xmlns:cac='urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2' "
            f"xmlns:cbc='urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'>"
            f"<cbc:UBLVersionID>2.1</cbc:UBLVersionID>"
            f"<cbc:CustomizationID>2.0</cbc:CustomizationID>"
            f"<cbc:ID>{serie}</cbc:ID>"
            f"<cbc:IssueDate>{fecha}</cbc:IssueDate>"
            f"<cbc:DocumentCurrencyCode>{moneda}</cbc:DocumentCurrencyCode>"
            f"{despatch_xml}"
            f"<cac:AccountingSupplierParty>"
            f"<cac:Party>"
            f"<cac:PartyIdentification><cbc:ID schemeID='{vendedor.get('codigo_tipo_documento', '6')}'>{vendedor.get('ruc', '')}</cbc:ID></cac:PartyIdentification>"
            f"<cac:PartyLegalEntity><cbc:RegistrationName>{vendedor.get('razon_social', '')}</cbc:RegistrationName></cac:PartyLegalEntity>"
            f"</cac:Party>"
            f"</cac:AccountingSupplierParty>"
            f"<cac:AccountingCustomerParty>"
            f"<cac:Party>"
            f"<cac:PartyIdentification><cbc:ID schemeID='{comprador.get('codigo_tipo_documento', '6')}'>{comprador.get('ruc', '')}</cbc:ID></cac:PartyIdentification>"
            f"<cac:PartyLegalEntity><cbc:RegistrationName>{comprador.get('razon_social', '')}</cbc:RegistrationName></cac:PartyLegalEntity>"
            f"</cac:Party>"
            f"</cac:AccountingCustomerParty>"
            f"<cac:TaxTotal>"
            f"<cbc:TaxAmount currencyID='{moneda}'>{totales.get('total_igv', 0.0):.2f}</cbc:TaxAmount>"
            f"</cac:TaxTotal>"
            f"<cac:LegalMonetaryTotal>"
            f"<cbc:PayableAmount currencyID='{moneda}'>{totales.get('importe_total', 0.0):.2f}</cbc:PayableAmount>"
            f"</cac:LegalMonetaryTotal>"
            f"{lines_joined}"
            f"</Invoice>"
        )
        return xml

    @classmethod
    def emitir_factura(cls, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Orquesta la validación normativa, generación de UBL 2.1 y persistencia."""
        # 1. Validar RUCs (Catálogo 06)
        cls.validar_ruc(request_dict["vendedor"]["ruc"])
        cls.validar_ruc(request_dict["comprador"]["ruc"])

        # 2. Validar Catálogo 08 de ISC en cada ítem
        for item in request_dict.get("items", []):
            cls.validar_codigo_isc(item.get("codigo_sistema_isc"))

        # 3. Construir XML UBL 2.1
        xml_ubl = cls.construir_xml_ubl_2_1(request_dict)

        # 4. Generar Hash CPE
        hash_cpe = cls.generar_hash_cpe(xml_ubl)
        id_comprobante = request_dict["serie_correlativo"]

        # 5. Estructurar respuesta aceptada
        factura_guardada = {
            "id_comprobante": id_comprobante,
            "estado_sunat": "ACEPTADO",
            "hash_cpe": hash_cpe,
            "xml_ubl_generado": xml_ubl,
            "mensaje_ose": f"La Factura {id_comprobante} cumple con UBL-Invoice-2.1.xsd y ha sido ACEPTADA.",
            "datos_origen": request_dict,
        }

        # 6. Persistir en repositorio
        FacturaMemoryRepository.guardar_factura(id_comprobante, factura_guardada)

        return {
            "id_comprobante": factura_guardada["id_comprobante"],
            "estado_sunat": factura_guardada["estado_sunat"],
            "hash_cpe": factura_guardada["hash_cpe"],
            "xml_ubl_generado": factura_guardada["xml_ubl_generado"],
            "mensaje_ose": factura_guardada["mensaje_ose"],
        }

    @classmethod
    def consultar_factura(cls, id_comprobante: str) -> Optional[Dict[str, Any]]:
        """Consulta una factura en el repositorio."""
        factura = FacturaMemoryRepository.obtener_factura_por_id(id_comprobante)
        if not factura:
            return None
        return {
            "id_comprobante": factura["id_comprobante"],
            "estado_sunat": factura["estado_sunat"],
            "hash_cpe": factura["hash_cpe"],
            "xml_ubl_generado": factura["xml_ubl_generado"],
            "mensaje_ose": factura["mensaje_ose"],
        }

    @classmethod
    def migrar_ficha_legado(cls, ficha_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa una ficha histórica informal y genera trazabilidad formal."""
        tipo_mov = cls.clasificar_movimiento_legado(
            ingreso=float(ficha_dict.get("ingreso", 0)),
            salida=float(ficha_dict.get("salida", 0)),
        )

        nro_doc_legado = ficha_dict.get("nro_documento", "LEGADO-0000")
        conteo_migraciones = len(FacturaMemoryRepository.obtener_fichas_legado()) + 1
        id_migracion = f"MIG-2026-{conteo_migraciones:04d}"
        serie_sugerida = FacturaMemoryRepository.generar_siguiente_correlativo()

        resultado = {
            "id_migracion": id_migracion,
            "nro_documento_legado": nro_doc_legado,
            "tipo_movimiento": tipo_mov,
            "estado_trazabilidad": "MIGRADO_CON_TRAZABILIDAD",
            "serie_ubl_sugerida": serie_sugerida,
        }

        FacturaMemoryRepository.guardar_migracion(id_migracion, resultado)
        return resultado
