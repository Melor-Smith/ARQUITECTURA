"""Adaptador ``GeneradorUBL``: dominio -> clases derivadas del XSD OASIS UBL 2.1 -> XML.

No hay plantillas ni concatenación de texto. Las clases de ``generated/`` las produce
``xsdata`` a partir de los XSD oficiales (``specs/contracts/ubl-2.1/xsd``; ver
``scripts/generar_clases_ubl.ps1``). Por eso:

* el serializador escapa ``&``, ``<`` y ``>``;
* el orden de los elementos es el que exige el XSD (por ejemplo, en una línea
  ``cac:TaxTotal`` va antes que ``cac:Item`` y ``cac:Price``);
* un elemento que no existe en el XSD ni siquiera se puede construir.

El XML se genera sin ``ext:UBLExtensions``: la firma la agrega el adaptador de firma.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.models.datatype import XmlDate, XmlTime

from src.adapters.outbound.ubl import ID_FIRMA, NAMESPACES
from src.adapters.outbound.ubl.generated.common import ubl_common_aggregate_components_2_1 as cac
from src.adapters.outbound.ubl.generated.common import ubl_common_basic_components_2_1 as cbc
from src.adapters.outbound.ubl.generated.maindoc.ubl_credit_note_2_1 import CreditNote
from src.adapters.outbound.ubl.generated.maindoc.ubl_debit_note_2_1 import DebitNote
from src.adapters.outbound.ubl.generated.maindoc.ubl_invoice_2_1 import Invoice
from src.domain.catalogos import TipoComprobante, TipoDocumentoRelacionado, Tributo
from src.domain.comprobante import Comprobante, Linea
from src.domain.tributos import CERO, TASA_IGV, redondear

_SUNAT = "PE:SUNAT"
_UNECE = "United Nations Economic Commission for Europe"


def _catalogo(numero: str) -> str:
    return f"urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo{numero}"


class GeneradorUblXsdata:
    def __init__(self, sangria: str | None = None, *, declarar_prefijos_de_firma: bool = False) -> None:
        """Opciones de presentación que usa el formulario ``/venta``. No cambian ningún dato del comprobante.

        * ``sangria``: el XML sale indentado, legible para una persona.
        * ``declarar_prefijos_de_firma``: ``<Invoice>`` declara también ``ext`` (CommonExtensionComponents-2) y
          ``ds`` (XMLDSig), como los ejemplos de SUNAT, aunque el XML aún no tenga firma. Así, quien agregue la
          firma después (por ejemplo, el OSE-DEMO de Nubefact al marcar "Firmar") puede insertar
          ``<ext:UBLExtensions>`` sin declarar el prefijo. Sin esto responde 0306: *The prefix "ext" for element
          "ext:UBLExtensions" is not bound*. Declarar un prefijo sin usarlo es válido (Namespaces in XML 1.0).

        Por defecto el XML es compacto y sin esas declaraciones: la emisión, los XML de referencia y la evidencia
        de SUNAT se comparan byte a byte. En todos los casos el XML valida contra el XSD.
        """
        self._serializador = XmlSerializer(
            config=SerializerConfig(xml_declaration=True, encoding="UTF-8", indent=sangria)
        )
        self._prefijos = ("cac", "cbc", "ext", "ds") if declarar_prefijos_de_firma else ("cac", "cbc")

    def generar(self, comprobante: Comprobante) -> bytes:
        documento, raiz = self._documento(comprobante)
        ns_map: dict[str | None, str] = {None: NAMESPACES[raiz]}
        ns_map.update({k: v for k, v in NAMESPACES.items() if k in self._prefijos})
        return self._serializador.render(documento, ns_map=ns_map).encode("utf-8")

    # --- documento ---------------------------------------------------------------------
    def _documento(self, c: Comprobante):
        moneda = c.moneda.value
        comunes: dict[str, Any] = dict(
            ublversion_id=cbc.UblversionId(value="2.1"),
            customization_id=cbc.CustomizationId(value="2.0", scheme_agency_name=_SUNAT),
            id=cbc.Id(value=c.serie_numero),
            issue_date=cbc.IssueDate(value=XmlDate.from_date(c.fecha_emision)),
            issue_time=cbc.IssueTime(value=XmlTime.from_time(c.hora_emision)),
            # Leyenda 1000 (Catálogo 52): importe total en letras.
            note=[cbc.Note(value=c.monto_en_letras, language_locale_id="1000")],
            document_currency_code=cbc.DocumentCurrencyCode(
                value=moneda, list_id="ISO 4217 Alpha", list_name="Currency", list_agency_name=_UNECE
            ),
            signature=[self._firma(c)],
            accounting_supplier_party=self._emisor(c),
            accounting_customer_party=self._cliente(c),
            tax_total=[self._tributos_documento(c)],
        )
        if c.tipo in (TipoComprobante.FACTURA, TipoComprobante.BOLETA):
            return Invoice(
                **comunes,
                invoice_type_code=cbc.InvoiceTypeCode(
                    value=c.tipo.value, list_id=c.tipo_operacion.value, list_agency_name=_SUNAT,
                    list_name="Tipo de Documento", list_uri=_catalogo("01"), name="Tipo de Operacion",
                ),
                additional_document_reference=[
                    cac.AdditionalDocumentReference(
                        id=cbc.Id(value=nro),
                        document_type_code=cbc.DocumentTypeCode(
                            value=TipoDocumentoRelacionado.OTROS.value, list_agency_name=_SUNAT,
                            list_name="Documento Relacionado", list_uri=_catalogo("12"),
                        ),
                    )
                    for nro in c.documentos_legado
                ],
                payment_terms=self._forma_pago(c),
                legal_monetary_total=cac.LegalMonetaryTotal(**self._totales(c)),
                invoice_line=[
                    cac.InvoiceLine(
                        invoiced_quantity=self._cantidad(cbc.InvoicedQuantity, ln), **self._linea(c, ln)
                    )
                    for ln in c.lineas
                ],
            ), "Invoice"
        referencia = c.referencia
        assert referencia is not None and c.motivo is not None
        discrepancia = cac.DiscrepancyResponse(
            reference_id=cbc.ReferenceId(value=referencia.serie_numero),
            response_code=cbc.ResponseCode(
                value=c.motivo.value, list_agency_name=_SUNAT,
                list_name="Tipo de nota de credito" if c.tipo is TipoComprobante.NOTA_CREDITO
                else "Tipo de nota de debito",
                list_uri=_catalogo("09" if c.tipo is TipoComprobante.NOTA_CREDITO else "10"),
            ),
            description=[cbc.Description(value=c.sustento or "")],
        )
        facturacion = cac.BillingReference(
            invoice_document_reference=cac.InvoiceDocumentReference(
                id=cbc.Id(value=referencia.serie_numero),
                document_type_code=cbc.DocumentTypeCode(
                    value=referencia.tipo.value, list_agency_name=_SUNAT, list_name="Tipo de Documento",
                    list_uri=_catalogo("01"),
                ),
            )
        )
        if c.tipo is TipoComprobante.NOTA_CREDITO:
            return CreditNote(
                **comunes,
                discrepancy_response=[discrepancia],
                billing_reference=[facturacion],
                legal_monetary_total=cac.LegalMonetaryTotal(**self._totales(c)),
                credit_note_line=[
                    cac.CreditNoteLine(
                        credited_quantity=self._cantidad(cbc.CreditedQuantity, ln), **self._linea(c, ln)
                    )
                    for ln in c.lineas
                ],
            ), "CreditNote"
        return DebitNote(
            **comunes,
            discrepancy_response=[discrepancia],
            billing_reference=[facturacion],
            requested_monetary_total=cac.RequestedMonetaryTotal(**self._totales(c)),
            debit_note_line=[
                cac.DebitNoteLine(debited_quantity=self._cantidad(cbc.DebitedQuantity, ln), **self._linea(c, ln))
                for ln in c.lineas
            ],
        ), "DebitNote"

    # --- forma de pago (RS 193-2020) ----------------------------------------------------
    @staticmethod
    def _forma_pago(c: Comprobante) -> list[cac.PaymentTerms]:
        """Contado: un PaymentTerms. Crédito: uno con el monto pendiente y uno por cuota (Cuota001, …)."""
        fp = c.forma_pago
        if fp is None:
            return []
        moneda = c.moneda.value
        terminos = [cac.PaymentTerms(
            id=cbc.Id(value="FormaPago"),
            payment_means_id=[cbc.PaymentMeansId(value=fp.tipo.value)],
            amount=cbc.Amount(value=fp.monto_pendiente, currency_id=moneda) if fp.es_credito else None,
        )]
        terminos.extend(
            cac.PaymentTerms(
                id=cbc.Id(value="FormaPago"),
                payment_means_id=[cbc.PaymentMeansId(value=f"Cuota{n:03d}")],
                amount=cbc.Amount(value=cuota.monto, currency_id=moneda),
                payment_due_date=cbc.PaymentDueDate(value=XmlDate.from_date(cuota.fecha_vencimiento)),
            )
            for n, cuota in enumerate(fp.cuotas, start=1)
        )
        return terminos

    # --- partes ------------------------------------------------------------------------
    @staticmethod
    def _firma(c: Comprobante) -> cac.Signature:
        """Referencia UBL a la firma XMLDSig que agrega el adaptador de firma."""
        return cac.Signature(
            id=cbc.Id(value=ID_FIRMA),
            signatory_party=cac.SignatoryParty(
                party_identification=[cac.PartyIdentification(id=cbc.Id(value=str(c.emisor.ruc)))],
                party_name=[cac.PartyName(name=cbc.Name(value=c.emisor.razon_social))],
            ),
            digital_signature_attachment=cac.DigitalSignatureAttachment(
                external_reference=cac.ExternalReference(uri=cbc.Uri(value=f"#{ID_FIRMA}"))
            ),
        )

    @staticmethod
    def _identificacion(tipo: str, numero: str) -> cac.PartyIdentification:
        return cac.PartyIdentification(
            id=cbc.Id(value=numero, scheme_id=tipo, scheme_name="Documento de Identidad",
                      scheme_agency_name=_SUNAT, scheme_uri=_catalogo("06"))
        )

    def _emisor(self, c: Comprobante) -> cac.AccountingSupplierParty:
        e = c.emisor
        return cac.AccountingSupplierParty(
            party=cac.Party(
                party_identification=[self._identificacion("6", str(e.ruc))],
                party_name=[cac.PartyName(name=cbc.Name(value=e.nombre_comercial))],
                party_legal_entity=[
                    cac.PartyLegalEntity(
                        registration_name=cbc.RegistrationName(value=e.razon_social),
                        registration_address=cac.RegistrationAddress(
                            id=cbc.Id(value=e.ubigeo, scheme_agency_name="PE:INEI", scheme_name="Ubigeos"),
                            address_type_code=cbc.AddressTypeCode(
                                value=e.codigo_establecimiento, list_agency_name=_SUNAT,
                                list_name="Establecimientos anexos",
                            ),
                            address_line=[cac.AddressLine(line=cbc.Line(value=e.direccion))],
                            country=cac.Country(identification_code=cbc.IdentificationCode(value="PE")),
                        ),
                    )
                ],
            )
        )

    def _cliente(self, c: Comprobante) -> cac.AccountingCustomerParty:
        cl = c.cliente
        direccion = (
            cac.RegistrationAddress(address_line=[cac.AddressLine(line=cbc.Line(value=cl.direccion))])
            if cl.direccion else None
        )
        return cac.AccountingCustomerParty(
            party=cac.Party(
                party_identification=[self._identificacion(cl.documento.tipo.value, cl.documento.numero)],
                party_legal_entity=[
                    cac.PartyLegalEntity(
                        registration_name=cbc.RegistrationName(value=cl.nombre), registration_address=direccion
                    )
                ],
            )
        )

    # --- tributos ----------------------------------------------------------------------
    @staticmethod
    def _esquema(tributo: Tributo) -> cac.TaxScheme:
        return cac.TaxScheme(
            id=cbc.Id(value=tributo.value, scheme_name="Codigo de tributos", scheme_agency_name=_SUNAT,
                      scheme_uri=_catalogo("05")),
            name=cbc.Name(value=tributo.nombre),
            tax_type_code=cbc.TaxTypeCode(value=tributo.codigo_internacional),
        )

    @staticmethod
    def _categoria_id(tributo: Tributo) -> cbc.Id:
        return cbc.Id(value=tributo.categoria, scheme_id="UN/ECE 5305", scheme_name="Tax Category Identifier",
                      scheme_agency_name=_UNECE)

    def _subtotal(self, tributo: Tributo, moneda: str, base: Decimal | None, monto: Decimal) -> cac.TaxSubtotal:
        return cac.TaxSubtotal(
            taxable_amount=cbc.TaxableAmount(value=base, currency_id=moneda) if base is not None else None,
            tax_amount=cbc.TaxAmount(value=monto, currency_id=moneda),
            tax_category=cac.TaxCategory(id=self._categoria_id(tributo), tax_scheme=self._esquema(tributo)),
        )

    def _tributos_documento(self, c: Comprobante) -> cac.TaxTotal:
        t, moneda = c.totales, c.moneda.value
        subtotales = []
        if t.gravadas or t.igv:
            # Regla 3277 de SUNAT: la base global del IGV es la suma de los valores de venta
            # gravados SIN el ISC (en la línea, en cambio, la base sí incluye el ISC).
            subtotales.append(self._subtotal(Tributo.IGV, moneda, t.gravadas, t.igv))
        if t.isc:
            subtotales.append(self._subtotal(Tributo.ISC, moneda, t.base_isc, t.isc))
        for monto, tributo in ((t.exoneradas, Tributo.EXONERADO), (t.inafectas, Tributo.INAFECTO),
                               (t.exportacion, Tributo.EXPORTACION)):
            if monto:
                subtotales.append(self._subtotal(tributo, moneda, monto, redondear(CERO)))
        if t.icbper:
            subtotales.append(self._subtotal(Tributo.ICBPER, moneda, None, t.icbper))
        return cac.TaxTotal(tax_amount=cbc.TaxAmount(value=t.total_impuestos, currency_id=moneda),
                            tax_subtotal=subtotales)

    @staticmethod
    def _totales(c: Comprobante) -> dict:
        moneda = c.moneda.value
        return dict(
            line_extension_amount=cbc.LineExtensionAmount(value=c.totales.valor_venta, currency_id=moneda),
            tax_inclusive_amount=cbc.TaxInclusiveAmount(value=c.totales.importe_total, currency_id=moneda),
            payable_amount=cbc.PayableAmount(value=c.totales.importe_total, currency_id=moneda),
        )

    # --- líneas ------------------------------------------------------------------------
    @staticmethod
    def _cantidad(clase, ln: Linea):
        """``unitCode`` sale del Catálogo 03 (UN/ECE Rec. 20) de cada línea; ya no es siempre NIU."""
        return clase(value=ln.cantidad, unit_code=ln.unidad.value, unit_code_list_id="UN/ECE rec 20",
                     unit_code_list_agency_name=_UNECE)

    def _linea(self, c: Comprobante, ln: Linea) -> dict:
        moneda = c.moneda.value
        subtotales = []
        if ln.isc is not None:
            subtotales.append(cac.TaxSubtotal(
                taxable_amount=cbc.TaxableAmount(value=ln.base_isc, currency_id=moneda),
                tax_amount=cbc.TaxAmount(value=ln.monto_isc, currency_id=moneda),
                tax_category=cac.TaxCategory(
                    id=self._categoria_id(Tributo.ISC),
                    percent=cbc.Percent(value=tasa) if (tasa := ln.tasa_isc_porcentual) is not None else None,
                    per_unit_amount=(cbc.PerUnitAmount(value=ln.isc.monto_fijo, currency_id=moneda)
                                     if ln.isc.monto_fijo is not None else None),
                    tier_range=cbc.TierRange(value=ln.isc.sistema.value),  # Catálogo 08
                    tax_scheme=self._esquema(Tributo.ISC),
                ),
            ))
        tributo_igv = ln.afectacion.tributo
        subtotales.append(cac.TaxSubtotal(
            taxable_amount=cbc.TaxableAmount(value=ln.base_igv, currency_id=moneda),
            tax_amount=cbc.TaxAmount(value=ln.monto_igv, currency_id=moneda),
            tax_category=cac.TaxCategory(
                id=self._categoria_id(tributo_igv),
                percent=cbc.Percent(value=(TASA_IGV * 100).quantize(Decimal("0.01")) if ln.afectacion.es_gravada
                                    else Decimal("0.00")),
                tax_exemption_reason_code=cbc.TaxExemptionReasonCode(  # Catálogo 07
                    value=ln.afectacion.value, list_agency_name=_SUNAT, list_name="Afectacion del IGV",
                    list_uri=_catalogo("07"),
                ),
                tax_scheme=self._esquema(tributo_igv),
            ),
        ))
        if ln.aplica_icbper:
            subtotales.append(cac.TaxSubtotal(
                tax_amount=cbc.TaxAmount(value=ln.monto_icbper, currency_id=moneda),
                base_unit_measure=cbc.BaseUnitMeasure(value=ln.cantidad, unit_code=ln.unidad.value),
                tax_category=cac.TaxCategory(
                    id=self._categoria_id(Tributo.ICBPER),
                    per_unit_amount=cbc.PerUnitAmount(value=ln.tasa_icbper, currency_id=moneda),
                    tax_scheme=self._esquema(Tributo.ICBPER),
                ),
            ))
        return dict(
            id=cbc.Id(value=str(ln.numero)),
            line_extension_amount=cbc.LineExtensionAmount(value=ln.valor_venta, currency_id=moneda),
            pricing_reference=cac.PricingReference(alternative_condition_price=[
                cac.AlternativeConditionPrice(
                    price_amount=cbc.PriceAmount(value=ln.precio_unitario, currency_id=moneda),
                    price_type_code=cbc.PriceTypeCode(value="01", list_agency_name=_SUNAT, list_name="Tipo de Precio",
                                                      list_uri=_catalogo("16")),
                )
            ]),
            tax_total=[cac.TaxTotal(tax_amount=cbc.TaxAmount(value=ln.total_tributos, currency_id=moneda),
                                    tax_subtotal=subtotales)],
            item=cac.Item(
                description=[cbc.Description(value=ln.descripcion)],
                sellers_item_identification=(
                    cac.SellersItemIdentification(id=cbc.Id(value=ln.codigo_producto)) if ln.codigo_producto else None
                ),
            ),
            price=cac.Price(price_amount=cbc.PriceAmount(value=ln.valor_unitario, currency_id=moneda)),
        )
