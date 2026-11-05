"""Adaptadores UBL 2.1: generación desde clases xsdata y validación contra el XSD oficial."""

from pathlib import Path

#: Identificador compartido por ``cac:Signature`` y ``ds:Signature/@Id``.
ID_FIRMA = "SignatureSP"

NAMESPACES: dict[str, str] = {
    "Invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "CreditNote": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "DebitNote": "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

#: XSD oficiales OASIS UBL 2.1 completos (maindoc + common).
DIRECTORIO_XSD = Path(__file__).resolve().parents[4] / "specs" / "contracts" / "ubl-2.1" / "xsd"
