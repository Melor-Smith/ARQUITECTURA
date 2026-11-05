from __future__ import annotations

from dataclasses import dataclass, field

from src.adapters.outbound.ubl.generated.common.ubl_common_basic_components_2_1 import (
    Id,
    Name,
)
from src.adapters.outbound.ubl.generated.common.ubl_extension_content_data_type_2_1 import (
    ExtensionContentType,
)
from src.adapters.outbound.ubl.generated.common.ubl_unqualified_data_types_2_1 import (
    CodeType,
    IdentifierType,
    TextType,
)

__NAMESPACE__ = (
    "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
)


@dataclass(kw_only=True)
class ExtensionAgencyIdtype(IdentifierType):
    class Meta:
        name = "ExtensionAgencyIDType"


@dataclass(kw_only=True)
class ExtensionAgencyNameType(TextType):
    pass


@dataclass(kw_only=True)
class ExtensionAgencyUritype(IdentifierType):
    class Meta:
        name = "ExtensionAgencyURIType"


@dataclass(kw_only=True)
class ExtensionContent(ExtensionContentType):
    class Meta:
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class ExtensionReasonCodeType(CodeType):
    pass


@dataclass(kw_only=True)
class ExtensionReasonType(TextType):
    pass


@dataclass(kw_only=True)
class ExtensionUritype(IdentifierType):
    class Meta:
        name = "ExtensionURIType"


@dataclass(kw_only=True)
class ExtensionVersionIdtype(IdentifierType):
    class Meta:
        name = "ExtensionVersionIDType"


@dataclass(kw_only=True)
class ExtensionAgencyId(ExtensionAgencyIdtype):
    class Meta:
        name = "ExtensionAgencyID"
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class ExtensionAgencyName(ExtensionAgencyNameType):
    class Meta:
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class ExtensionAgencyUri(ExtensionAgencyUritype):
    class Meta:
        name = "ExtensionAgencyURI"
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class ExtensionReason(ExtensionReasonType):
    class Meta:
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class ExtensionReasonCode(ExtensionReasonCodeType):
    class Meta:
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class ExtensionUri(ExtensionUritype):
    class Meta:
        name = "ExtensionURI"
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class ExtensionVersionId(ExtensionVersionIdtype):
    class Meta:
        name = "ExtensionVersionID"
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class UblextensionType:
    """
    A single extension for private use.

    :ivar id: An identifier for the Extension assigned by the creator of
        the extension.
    :ivar name: A name for the Extension assigned by the creator of the
        extension.
    :ivar extension_agency_id: An agency that maintains one or more
        Extensions.
    :ivar extension_agency_name: The name of the agency that maintains
        the Extension.
    :ivar extension_version_id: The version of the Extension.
    :ivar extension_agency_uri: A URI for the Agency that maintains the
        Extension.
    :ivar extension_uri: A URI for the Extension.
    :ivar extension_reason_code: A code for reason the Extension is
        being included.
    :ivar extension_reason: A description of the reason for the
        Extension.
    :ivar extension_content: The definition of the extension content.
    """

    class Meta:
        name = "UBLExtensionType"

    id: None | Id = field(
        default=None,
        metadata={
            "name": "ID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    name: None | Name = field(
        default=None,
        metadata={
            "name": "Name",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
        },
    )
    extension_agency_id: None | ExtensionAgencyId = field(
        default=None,
        metadata={
            "name": "ExtensionAgencyID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_agency_name: None | ExtensionAgencyName = field(
        default=None,
        metadata={
            "name": "ExtensionAgencyName",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_version_id: None | ExtensionVersionId = field(
        default=None,
        metadata={
            "name": "ExtensionVersionID",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_agency_uri: None | ExtensionAgencyUri = field(
        default=None,
        metadata={
            "name": "ExtensionAgencyURI",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_uri: None | ExtensionUri = field(
        default=None,
        metadata={
            "name": "ExtensionURI",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_reason_code: None | ExtensionReasonCode = field(
        default=None,
        metadata={
            "name": "ExtensionReasonCode",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_reason: None | ExtensionReason = field(
        default=None,
        metadata={
            "name": "ExtensionReason",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        },
    )
    extension_content: ExtensionContent = field(
        metadata={
            "name": "ExtensionContent",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        }
    )


@dataclass(kw_only=True)
class Ublextension(UblextensionType):
    """
    A single extension for private use.
    """

    class Meta:
        name = "UBLExtension"
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"


@dataclass(kw_only=True)
class UblextensionsType:
    """
    A container for all extensions present in the document.

    :ivar ublextension: A single extension for private use.
    """

    class Meta:
        name = "UBLExtensionsType"

    ublextension: list[Ublextension] = field(
        default_factory=list,
        metadata={
            "name": "UBLExtension",
            "type": "Element",
            "namespace": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
            "min_occurs": 1,
        },
    )


@dataclass(kw_only=True)
class Ublextensions(UblextensionsType):
    """
    A container for all extensions present in the document.
    """

    class Meta:
        name = "UBLExtensions"
        namespace = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
