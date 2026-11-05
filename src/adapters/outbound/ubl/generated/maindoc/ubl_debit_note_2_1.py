from __future__ import annotations

from dataclasses import dataclass, field

from src.adapters.outbound.ubl.generated.common.ubl_common_aggregate_components_2_1 import (
    AccountingCustomerParty,
    AccountingSupplierParty,
    AdditionalDocumentReference,
    AllowanceCharge,
    BillingReference,
    BuyerCustomerParty,
    ContractDocumentReference,
    DebitNoteLine,
    Delivery,
    DeliveryTerms,
    DespatchDocumentReference,
    DiscrepancyResponse,
    InvoicePeriod,
    OrderReference,
    PayeeParty,
    PaymentAlternativeExchangeRate,
    PaymentExchangeRate,
    PaymentMeans,
    PaymentTerms,
    PrepaidPayment,
    PricingExchangeRate,
    ReceiptDocumentReference,
    RequestedMonetaryTotal,
    SellerSupplierParty,
    Signature,
    StatementDocumentReference,
    TaxExchangeRate,
    TaxRepresentativeParty,
    TaxTotal,
)
from src.adapters.outbound.ubl.generated.common.ubl_common_basic_components_2_1 import (
    AccountingCost,
    AccountingCostCode,
    CopyIndicator,
    CustomizationId,
    DocumentCurrencyCode,
    Id,
    IssueDate,
    IssueTime,
    LineCountNumeric,
    Note,
    PaymentAlternativeCurrencyCode,
    PaymentCurrencyCode,
    PricingCurrencyCode,
    ProfileExecutionId,
    ProfileId,
    TaxCurrencyCode,
    TaxPointDate,
    UblversionId,
    Uuid,
)
from src.adapters.outbound.ubl.generated.common.ubl_common_extension_components_2_1 import (
    Ublextensions,
)

__NAMESPACE__ = "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2"


@dataclass(kw_only=True)
class DebitNoteType:
    """
    <ns1:Component xmlns:ns1="urn:un:unece:uncefact:documentation:2">
    <ns1:ComponentType>ABIE</ns1:ComponentType>
    <ns1:DictionaryEntryName>Debit Note.

    Details</ns1:DictionaryEntryName> <ns1:Definition>A document used to
    specify debts incurred by the Debtor.</ns1:Definition>
    <ns1:ObjectClass>Debit Note</ns1:ObjectClass> </ns1:Component>.

    :ivar ublextensions: A container for all extensions present in the
        document.
    :ivar ublversion_id: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. UBL Version Identifier.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition>Identifies
        the earliest version of the UBL 2 schema for this document type
        that defines all of the elements that might be encountered in
        the current instance.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>UBL Version
        Identifier</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType>
        <ns1:Examples>2.0.5</ns1:Examples> </ns1:Component>
    :ivar customization_id: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Customization Identifier.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition>Identifies
        a user-defined customization of UBL for a specific
        use.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Customization Identifier</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType>
        <ns1:Examples>NES</ns1:Examples> </ns1:Component>
    :ivar profile_id: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Profile Identifier.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition>Identifies
        a user-defined profile of the customization of UBL being
        used.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Profile Identifier</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType>
        <ns1:Examples>BasicProcurementProcess</ns1:Examples>
        </ns1:Component>
    :ivar profile_execution_id: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Profile Execution
        Identifier. Identifier</ns1:DictionaryEntryName>
        <ns1:Definition>Identifies an instance of executing a profile,
        to associate all transactions in a
        collaboration.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Profile Execution
        Identifier</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType>
        <ns1:Examples>BPP-1001</ns1:Examples> </ns1:Component>
    :ivar id: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition>An
        identifier for this document, assigned by the
        sender.</ns1:Definition> <ns1:Cardinality>1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Identifier</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType> </ns1:Component>
    :ivar copy_indicator: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Copy_ Indicator.
        Indicator</ns1:DictionaryEntryName> <ns1:Definition>Indicates
        whether this document is a copy (true) or not
        (false).</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Copy</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Indicator</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Indicator</ns1:RepresentationTerm>
        <ns1:DataType>Indicator. Type</ns1:DataType> </ns1:Component>
    :ivar uuid: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. UUID.
        Identifier</ns1:DictionaryEntryName> <ns1:Definition>A
        universally unique identifier for an instance of this
        document.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>UUID</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Identifier</ns1:RepresentationTerm>
        <ns1:DataType>Identifier. Type</ns1:DataType> </ns1:Component>
    :ivar issue_date: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Issue Date.
        Date</ns1:DictionaryEntryName> <ns1:Definition>The date,
        assigned by the sender, on which this document was
        issued.</ns1:Definition> <ns1:Cardinality>1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Issue Date</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Date</ns1:RepresentationTerm>
        <ns1:DataType>Date. Type</ns1:DataType> </ns1:Component>
    :ivar issue_time: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Issue Time.
        Time</ns1:DictionaryEntryName> <ns1:Definition>The time,
        assigned by the sender, at which this document was
        issued.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Issue Time</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Time</ns1:RepresentationTerm>
        <ns1:DataType>Time. Type</ns1:DataType> </ns1:Component>
    :ivar note: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Note.
        Text</ns1:DictionaryEntryName> <ns1:Definition>Free-form text
        pertinent to this document, conveying information that is not
        contained explicitly in other structures.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Note</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Text</ns1:RepresentationTerm>
        <ns1:DataType>Text. Type</ns1:DataType> </ns1:Component>
    :ivar tax_point_date: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Tax Point Date.
        Date</ns1:DictionaryEntryName> <ns1:Definition>The date of the
        Debit Note, used to indicate the point at which tax becomes
        applicable.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Tax Point
        Date</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Date</ns1:RepresentationTerm>
        <ns1:DataType>Date. Type</ns1:DataType> </ns1:Component>
    :ivar document_currency_code: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Document_ Currency Code.
        Code</ns1:DictionaryEntryName> <ns1:Definition>A code signifying
        the default currency for this document.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Document</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Currency Code</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Code</ns1:RepresentationTerm>
        <ns1:DataTypeQualifier>Currency</ns1:DataTypeQualifier>
        <ns1:DataType>Currency_ Code. Type</ns1:DataType>
        </ns1:Component>
    :ivar tax_currency_code: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Tax_ Currency Code.
        Code</ns1:DictionaryEntryName> <ns1:Definition>A code signifying
        the currency used for tax amounts in the Debit
        Note.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Tax</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Currency Code</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Code</ns1:RepresentationTerm>
        <ns1:DataTypeQualifier>Currency</ns1:DataTypeQualifier>
        <ns1:DataType>Currency_ Code. Type</ns1:DataType>
        </ns1:Component>
    :ivar pricing_currency_code: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Pricing_ Currency Code.
        Code</ns1:DictionaryEntryName> <ns1:Definition>A code signifying
        the currency used for prices in the Debit Note.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Pricing</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Currency Code</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Code</ns1:RepresentationTerm>
        <ns1:DataTypeQualifier>Currency</ns1:DataTypeQualifier>
        <ns1:DataType>Currency_ Code. Type</ns1:DataType>
        </ns1:Component>
    :ivar payment_currency_code: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Payment_ Currency Code.
        Code</ns1:DictionaryEntryName> <ns1:Definition>A code signifying
        the currency used for payment in the Debit
        Note.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Payment</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Currency Code</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Code</ns1:RepresentationTerm>
        <ns1:DataTypeQualifier>Currency</ns1:DataTypeQualifier>
        <ns1:DataType>Currency_ Code. Type</ns1:DataType>
        </ns1:Component>
    :ivar payment_alternative_currency_code: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Payment Alternative_
        Currency Code. Code</ns1:DictionaryEntryName> <ns1:Definition>A
        code signifying the alternative currency used for payment in the
        Debit Note.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTermQualifier>Payment
        Alternative</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Currency Code</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Code</ns1:RepresentationTerm>
        <ns1:DataTypeQualifier>Currency</ns1:DataTypeQualifier>
        <ns1:DataType>Currency_ Code. Type</ns1:DataType>
        </ns1:Component>
    :ivar accounting_cost_code: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Accounting Cost Code.
        Code</ns1:DictionaryEntryName> <ns1:Definition>The Buyer's
        accounting code, applied to the Credit Note as a
        whole.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Accounting Cost Code</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Code</ns1:RepresentationTerm>
        <ns1:DataType>Code. Type</ns1:DataType> </ns1:Component>
    :ivar accounting_cost: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Accounting Cost.
        Text</ns1:DictionaryEntryName> <ns1:Definition>The Buyer's
        accounting code, applied to the Credit Note as a whole,
        expressed as text.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Accounting
        Cost</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Text</ns1:RepresentationTerm>
        <ns1:DataType>Text. Type</ns1:DataType> </ns1:Component>
    :ivar line_count_numeric: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>BBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Line Count.
        Numeric</ns1:DictionaryEntryName> <ns1:Definition>The number of
        Debit Note Lines in this document.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Line
        Count</ns1:PropertyTerm>
        <ns1:RepresentationTerm>Numeric</ns1:RepresentationTerm>
        <ns1:DataType>Numeric. Type</ns1:DataType> </ns1:Component>
    :ivar invoice_period: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Invoice_ Period.
        Period</ns1:DictionaryEntryName> <ns1:Definition>A period
        (rather than a specific invoice) associated with this
        document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Invoice</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Period</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Period</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Period</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar discrepancy_response: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Discrepancy_ Response.
        Response</ns1:DictionaryEntryName> <ns1:Definition>A reason for
        the Debit Note as a whole.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Discrepancy</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Response</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Response</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Response</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar order_reference: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Order
        Reference</ns1:DictionaryEntryName> <ns1:Definition>A reference
        to an Order with which this Debit Note is
        associated.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Order
        Reference</ns1:PropertyTerm> <ns1:AssociatedObjectClass>Order
        Reference</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Order Reference</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar billing_reference: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Billing
        Reference</ns1:DictionaryEntryName> <ns1:Definition>A reference
        to a billing document associated with this
        document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Billing
        Reference</ns1:PropertyTerm> <ns1:AssociatedObjectClass>Billing
        Reference</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Billing
        Reference</ns1:RepresentationTerm> </ns1:Component>
    :ivar despatch_document_reference: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Despatch_ Document
        Reference. Document Reference</ns1:DictionaryEntryName>
        <ns1:Definition>A reference to a Despatch Advice associated with
        this document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Despatch</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Document Reference</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Document
        Reference</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Document
        Reference</ns1:RepresentationTerm> </ns1:Component>
    :ivar receipt_document_reference: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Receipt_ Document
        Reference. Document Reference</ns1:DictionaryEntryName>
        <ns1:Definition>A reference to a Receipt Advice associated with
        this document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Receipt</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Document Reference</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Document
        Reference</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Document
        Reference</ns1:RepresentationTerm> </ns1:Component>
    :ivar statement_document_reference: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Statement_ Document
        Reference. Document Reference</ns1:DictionaryEntryName>
        <ns1:Definition>A reference to a Statement associated with this
        document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Statement</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Document Reference</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Document
        Reference</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Document
        Reference</ns1:RepresentationTerm> </ns1:Component>
    :ivar contract_document_reference: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Contract_ Document
        Reference. Document Reference</ns1:DictionaryEntryName>
        <ns1:Definition>A reference to a contract associated with this
        document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Contract</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Document Reference</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Document
        Reference</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Document
        Reference</ns1:RepresentationTerm> </ns1:Component>
    :ivar additional_document_reference: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Additional_ Document
        Reference. Document Reference</ns1:DictionaryEntryName>
        <ns1:Definition>A reference to an additional document associated
        with this document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Additional</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Document Reference</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Document
        Reference</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Document
        Reference</ns1:RepresentationTerm> </ns1:Component>
    :ivar signature: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note.
        Signature</ns1:DictionaryEntryName> <ns1:Definition>A signature
        applied to this document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Signature</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Signature</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Signature</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar accounting_supplier_party: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Accounting_ Supplier Party.
        Supplier Party</ns1:DictionaryEntryName> <ns1:Definition>The
        accounting supplier party.</ns1:Definition>
        <ns1:Cardinality>1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Accounting</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Supplier Party</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Supplier
        Party</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Supplier Party</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar accounting_customer_party: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Accounting_ Customer Party.
        Customer Party</ns1:DictionaryEntryName> <ns1:Definition>The
        accounting customer party.</ns1:Definition>
        <ns1:Cardinality>1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Accounting</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Customer Party</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Customer
        Party</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Customer Party</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar payee_party: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Payee_ Party.
        Party</ns1:DictionaryEntryName> <ns1:Definition>The
        payee.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Payee</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Party</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Party</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Party</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar buyer_customer_party: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Buyer_ Customer Party.
        Customer Party</ns1:DictionaryEntryName> <ns1:Definition>The
        buyer.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Buyer</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Customer Party</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Customer
        Party</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Customer Party</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar seller_supplier_party: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Seller_ Supplier Party.
        Supplier Party</ns1:DictionaryEntryName> <ns1:Definition>The
        seller.</ns1:Definition> <ns1:Cardinality>0..1</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Seller</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Supplier Party</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Supplier
        Party</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Supplier Party</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar tax_representative_party: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Tax Representative_ Party.
        Party</ns1:DictionaryEntryName> <ns1:Definition>The tax
        representative.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTermQualifier>Tax
        Representative</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Party</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Party</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Party</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar prepaid_payment: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Prepaid_ Payment.
        Payment</ns1:DictionaryEntryName> <ns1:Definition>A prepaid
        payment.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Prepaid</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Payment</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Payment</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Payment</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar allowance_charge: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Allowance
        Charge</ns1:DictionaryEntryName> <ns1:Definition>A discount or
        charge that applies to a price component.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Allowance
        Charge</ns1:PropertyTerm> <ns1:AssociatedObjectClass>Allowance
        Charge</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Allowance
        Charge</ns1:RepresentationTerm> </ns1:Component>
    :ivar delivery: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note.
        Delivery</ns1:DictionaryEntryName> <ns1:Definition>A delivery
        associated with this document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Delivery</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Delivery</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Delivery</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar delivery_terms: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Delivery
        Terms</ns1:DictionaryEntryName> <ns1:Definition>A set of
        delivery terms associated with this document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Delivery
        Terms</ns1:PropertyTerm> <ns1:AssociatedObjectClass>Delivery
        Terms</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Delivery Terms</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar payment_means: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Payment
        Means</ns1:DictionaryEntryName> <ns1:Definition>Expected means
        of payment.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Payment
        Means</ns1:PropertyTerm> <ns1:AssociatedObjectClass>Payment
        Means</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Payment Means</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar payment_terms: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Payment
        Terms</ns1:DictionaryEntryName> <ns1:Definition>A set of payment
        terms associated with this document.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Payment
        Terms</ns1:PropertyTerm> <ns1:AssociatedObjectClass>Payment
        Terms</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Payment Terms</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar tax_exchange_rate: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Tax_ Exchange Rate.
        Exchange Rate</ns1:DictionaryEntryName> <ns1:Definition>The
        exchange rate between the document currency and the tax
        currency.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Tax</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Exchange Rate</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Exchange
        Rate</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Exchange Rate</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar pricing_exchange_rate: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Pricing_ Exchange Rate.
        Exchange Rate</ns1:DictionaryEntryName> <ns1:Definition>The
        exchange rate between the document currency and the pricing
        currency.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Pricing</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Exchange Rate</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Exchange
        Rate</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Exchange Rate</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar payment_exchange_rate: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Payment_ Exchange Rate.
        Exchange Rate</ns1:DictionaryEntryName> <ns1:Definition>The
        exchange rate between the document currency and the payment
        currency.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Payment</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Exchange Rate</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Exchange
        Rate</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Exchange Rate</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar payment_alternative_exchange_rate: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Payment Alternative_
        Exchange Rate. Exchange Rate</ns1:DictionaryEntryName>
        <ns1:Definition>The exchange rate between the document currency
        and the payment alternative currency.</ns1:Definition>
        <ns1:Cardinality>0..1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTermQualifier>Payment
        Alternative</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Exchange Rate</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Exchange
        Rate</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Exchange Rate</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar tax_total: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Tax
        Total</ns1:DictionaryEntryName> <ns1:Definition>The total amount
        of a specific type of tax.</ns1:Definition>
        <ns1:Cardinality>0..n</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass> <ns1:PropertyTerm>Tax
        Total</ns1:PropertyTerm> <ns1:AssociatedObjectClass>Tax
        Total</ns1:AssociatedObjectClass> <ns1:RepresentationTerm>Tax
        Total</ns1:RepresentationTerm> </ns1:Component>
    :ivar requested_monetary_total: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Requested_ Monetary Total.
        Monetary Total</ns1:DictionaryEntryName> <ns1:Definition>The
        total amount payable on the Debit Note, including allowances,
        charges, and taxes.</ns1:Definition>
        <ns1:Cardinality>1</ns1:Cardinality> <ns1:ObjectClass>Debit
        Note</ns1:ObjectClass>
        <ns1:PropertyTermQualifier>Requested</ns1:PropertyTermQualifier>
        <ns1:PropertyTerm>Monetary Total</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Monetary
        Total</ns1:AssociatedObjectClass>
        <ns1:RepresentationTerm>Monetary Total</ns1:RepresentationTerm>
        </ns1:Component>
    :ivar debit_note_line: <ns1:Component
        xmlns:ns1="urn:un:unece:uncefact:documentation:2">
        <ns1:ComponentType>ASBIE</ns1:ComponentType>
        <ns1:DictionaryEntryName>Debit Note. Debit Note
        Line</ns1:DictionaryEntryName> <ns1:Definition>A Debit Note
        line.</ns1:Definition> <ns1:Cardinality>1..n</ns1:Cardinality>
        <ns1:ObjectClass>Debit Note</ns1:ObjectClass>
        <ns1:PropertyTerm>Debit Note Line</ns1:PropertyTerm>
        <ns1:AssociatedObjectClass>Debit Note
        Line</ns1:AssociatedObjectClass> <ns1:RepresentationTerm>Debit
        Note Line</ns1:RepresentationTerm> </ns1:Component>
    """

    ublextensions: None | Ublextensions = field(
        default=None,
        metadata={
            "name": "UBLExtensions",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    ublversion_id: None | UblversionId = field(
        default=None,
        metadata={
            "name": "UBLVersionID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    customization_id: None | CustomizationId = field(
        default=None,
        metadata={
            "name": "CustomizationID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    profile_id: None | ProfileId = field(
        default=None,
        metadata={
            "name": "ProfileID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    profile_execution_id: None | ProfileExecutionId = field(
        default=None,
        metadata={
            "name": "ProfileExecutionID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    id: Id = field(
        metadata={
            "name": "ID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        }
    )
    copy_indicator: None | CopyIndicator = field(
        default=None,
        metadata={
            "name": "CopyIndicator",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    uuid: None | Uuid = field(
        default=None,
        metadata={
            "name": "UUID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    issue_date: IssueDate = field(
        metadata={
            "name": "IssueDate",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        }
    )
    issue_time: None | IssueTime = field(
        default=None,
        metadata={
            "name": "IssueTime",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    note: list[Note] = field(
        default_factory=list,
        metadata={
            "name": "Note",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    tax_point_date: None | TaxPointDate = field(
        default=None,
        metadata={
            "name": "TaxPointDate",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    document_currency_code: None | DocumentCurrencyCode = field(
        default=None,
        metadata={
            "name": "DocumentCurrencyCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    tax_currency_code: None | TaxCurrencyCode = field(
        default=None,
        metadata={
            "name": "TaxCurrencyCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    pricing_currency_code: None | PricingCurrencyCode = field(
        default=None,
        metadata={
            "name": "PricingCurrencyCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    payment_currency_code: None | PaymentCurrencyCode = field(
        default=None,
        metadata={
            "name": "PaymentCurrencyCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    payment_alternative_currency_code: (
        None | PaymentAlternativeCurrencyCode
    ) = field(
        default=None,
        metadata={
            "name": "PaymentAlternativeCurrencyCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    accounting_cost_code: None | AccountingCostCode = field(
        default=None,
        metadata={
            "name": "AccountingCostCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    accounting_cost: None | AccountingCost = field(
        default=None,
        metadata={
            "name": "AccountingCost",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    line_count_numeric: None | LineCountNumeric = field(
        default=None,
        metadata={
            "name": "LineCountNumeric",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    invoice_period: list[InvoicePeriod] = field(
        default_factory=list,
        metadata={
            "name": "InvoicePeriod",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    discrepancy_response: list[DiscrepancyResponse] = field(
        default_factory=list,
        metadata={
            "name": "DiscrepancyResponse",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    order_reference: None | OrderReference = field(
        default=None,
        metadata={
            "name": "OrderReference",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    billing_reference: list[BillingReference] = field(
        default_factory=list,
        metadata={
            "name": "BillingReference",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    despatch_document_reference: list[DespatchDocumentReference] = field(
        default_factory=list,
        metadata={
            "name": "DespatchDocumentReference",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    receipt_document_reference: list[ReceiptDocumentReference] = field(
        default_factory=list,
        metadata={
            "name": "ReceiptDocumentReference",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    statement_document_reference: list[StatementDocumentReference] = field(
        default_factory=list,
        metadata={
            "name": "StatementDocumentReference",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    contract_document_reference: list[ContractDocumentReference] = field(
        default_factory=list,
        metadata={
            "name": "ContractDocumentReference",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    additional_document_reference: list[AdditionalDocumentReference] = field(
        default_factory=list,
        metadata={
            "name": "AdditionalDocumentReference",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    signature: list[Signature] = field(
        default_factory=list,
        metadata={
            "name": "Signature",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    accounting_supplier_party: AccountingSupplierParty = field(
        metadata={
            "name": "AccountingSupplierParty",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }
    )
    accounting_customer_party: AccountingCustomerParty = field(
        metadata={
            "name": "AccountingCustomerParty",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }
    )
    payee_party: None | PayeeParty = field(
        default=None,
        metadata={
            "name": "PayeeParty",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    buyer_customer_party: None | BuyerCustomerParty = field(
        default=None,
        metadata={
            "name": "BuyerCustomerParty",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    seller_supplier_party: None | SellerSupplierParty = field(
        default=None,
        metadata={
            "name": "SellerSupplierParty",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    tax_representative_party: None | TaxRepresentativeParty = field(
        default=None,
        metadata={
            "name": "TaxRepresentativeParty",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    prepaid_payment: list[PrepaidPayment] = field(
        default_factory=list,
        metadata={
            "name": "PrepaidPayment",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    allowance_charge: list[AllowanceCharge] = field(
        default_factory=list,
        metadata={
            "name": "AllowanceCharge",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    delivery: list[Delivery] = field(
        default_factory=list,
        metadata={
            "name": "Delivery",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    delivery_terms: list[DeliveryTerms] = field(
        default_factory=list,
        metadata={
            "name": "DeliveryTerms",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    payment_means: list[PaymentMeans] = field(
        default_factory=list,
        metadata={
            "name": "PaymentMeans",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    payment_terms: list[PaymentTerms] = field(
        default_factory=list,
        metadata={
            "name": "PaymentTerms",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    tax_exchange_rate: None | TaxExchangeRate = field(
        default=None,
        metadata={
            "name": "TaxExchangeRate",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    pricing_exchange_rate: None | PricingExchangeRate = field(
        default=None,
        metadata={
            "name": "PricingExchangeRate",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    payment_exchange_rate: None | PaymentExchangeRate = field(
        default=None,
        metadata={
            "name": "PaymentExchangeRate",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    payment_alternative_exchange_rate: (
        None | PaymentAlternativeExchangeRate
    ) = field(
        default=None,
        metadata={
            "name": "PaymentAlternativeExchangeRate",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    tax_total: list[TaxTotal] = field(
        default_factory=list,
        metadata={
            "name": "TaxTotal",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        },
    )
    requested_monetary_total: RequestedMonetaryTotal = field(
        metadata={
            "name": "RequestedMonetaryTotal",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }
    )
    debit_note_line: list[DebitNoteLine] = field(
        default_factory=list,
        metadata={
            "name": "DebitNoteLine",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "min_occurs": 1,
        },
    )


@dataclass(kw_only=True)
class DebitNote(DebitNoteType):
    """
    This element MUST be conveyed as the root element in any instance
    document based on this Schema expression.
    """

    class Meta:
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2"
