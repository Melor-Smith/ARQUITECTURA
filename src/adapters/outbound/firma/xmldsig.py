"""Adaptador ``FirmaDigital``: firma XMLDSig enveloped con signxml.

La firma se coloca en ``ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent`` como
exige SUNAT. El "hash CPE" que va en la representación impresa es el ``ds:DigestValue``
de esa firma, no un SHA-256 del XML sin firmar.

En producción se carga el certificado digital (.pfx) del emisor. En desarrollo se genera
un certificado autofirmado en memoria: nunca se versiona una clave privada.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import CanonicalizationMethod, DigestAlgorithm, SignatureMethod, XMLSigner, methods

from src.adapters.outbound.ubl import ID_FIRMA, NAMESPACES
from src.adapters.outbound.ubl.validador import parser_seguro
from src.application.puertos import DocumentoFirmado

_EXT = NAMESPACES["ext"]
_DS = NAMESPACES["ds"]


@dataclass(frozen=True)
class CertificadoDigital:
    clave_privada: rsa.RSAPrivateKey
    certificado_pem: bytes

    @classmethod
    def desde_pfx(cls, ruta: Path, contrasena: str) -> CertificadoDigital:
        clave, certificado, _ = pkcs12.load_key_and_certificates(ruta.read_bytes(), contrasena.encode())
        if clave is None or certificado is None:
            raise ValueError(f"El archivo {ruta} no contiene clave privada y certificado.")
        return cls(clave, certificado.public_bytes(serialization.Encoding.PEM))  # type: ignore[arg-type]

    @classmethod
    def autofirmado_para_desarrollo(cls, ruc: str, razon_social: str) -> CertificadoDigital:
        clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        nombre = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"{razon_social} (DESARROLLO)"),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, ruc),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PE"),
        ])
        ahora = dt.datetime.now(dt.timezone.utc)
        certificado = (
            x509.CertificateBuilder()
            .subject_name(nombre)
            .issuer_name(nombre)
            .public_key(clave.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(ahora - dt.timedelta(days=1))
            .not_valid_after(ahora + dt.timedelta(days=365))
            .sign(clave, hashes.SHA256())
        )
        return cls(clave, certificado.public_bytes(serialization.Encoding.PEM))


class FirmaXmlDsig:
    def __init__(self, certificado: CertificadoDigital) -> None:
        self._certificado = certificado
        self._firmador = XMLSigner(
            method=methods.enveloped,
            signature_algorithm=SignatureMethod.RSA_SHA256,
            digest_algorithm=DigestAlgorithm.SHA256,
            c14n_algorithm=CanonicalizationMethod.CANONICAL_XML_1_0,
        )

    def firmar(self, xml: bytes) -> DocumentoFirmado:
        raiz = etree.fromstring(xml, parser_seguro())
        extensiones = etree.Element(f"{{{_EXT}}}UBLExtensions", nsmap={"ext": _EXT})
        contenido = etree.SubElement(etree.SubElement(extensiones, f"{{{_EXT}}}UBLExtension"),
                                     f"{{{_EXT}}}ExtensionContent")
        # signxml reemplaza este marcador por la firma, en este lugar exacto del documento.
        etree.SubElement(contenido, f"{{{_DS}}}Signature", Id="placeholder", nsmap={"ds": _DS})
        raiz.insert(0, extensiones)
        # Si el XML viene indentado, la firma conserva la sangría; en el XML compacto (sin texto) no cambia nada.
        extensiones.tail = raiz.text

        firmado = self._firmador.sign(raiz, key=self._certificado.clave_privada,
                                      cert=self._certificado.certificado_pem.decode("ascii"))
        firma = firmado.find(f".//{{{_DS}}}Signature")
        # El Id no forma parte de lo firmado (la transformación enveloped excluye ds:Signature).
        firma.set("Id", ID_FIRMA)
        digest = firmado.find(f".//{{{_DS}}}DigestValue").text
        return DocumentoFirmado(etree.tostring(firmado, xml_declaration=True, encoding="UTF-8"), digest)
