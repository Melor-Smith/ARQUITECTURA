"""Adaptador ``ClienteOSE`` simulado (entorno de desarrollo y pruebas).

No es un "ACEPTADO" fijo: hace lo que hace una OSE antes de emitir el CDR.

1. Verifica la firma XMLDSig con el certificado incluido en ``ds:KeyInfo``.
2. Valida el XML contra el XSD UBL 2.1.
3. Responde con un CDR (código 0 = aceptado) o con el código de rechazo correspondiente.

Los modos ``CAIDA`` y ``RESPUESTA_INVALIDA`` permiten ejercitar los caminos 202, 502 y 503.
El adaptador real (SOAP ``sendBill`` de SUNAT o REST de una OSE) implementa el mismo
puerto y se elige en ``src/bootstrap.py``.
"""

from __future__ import annotations

from enum import Enum

from lxml import etree
from signxml import XMLVerifier
from signxml.exceptions import InvalidInput, InvalidSignature

from src.adapters.outbound.ubl import NAMESPACES
from src.adapters.outbound.ubl.validador import parser_seguro
from src.application.errores import OseNoDisponible, OseRespuestaInvalida, XmlNoConformeXsd
from src.application.puertos import Reloj, ValidadorEsquemaUBL
from src.domain.catalogos import TipoComprobante
from src.domain.comprobante import Cdr


class ModoOse(str, Enum):
    NORMAL = "NORMAL"
    CAIDA = "CAIDA"
    RESPUESTA_INVALIDA = "RESPUESTA_INVALIDA"
    RECHAZO = "RECHAZO"


class OseSimulada:
    def __init__(self, *, validador: ValidadorEsquemaUBL, reloj: Reloj, modo: ModoOse = ModoOse.NORMAL) -> None:
        self._validador = validador
        self._reloj = reloj
        self.modo = modo

    def enviar(self, nombre_archivo: str, xml_firmado: bytes) -> Cdr:
        if self.modo is ModoOse.CAIDA:
            raise OseNoDisponible("La OSE no respondió dentro del tiempo de espera.", reintentar_en_segundos=120)
        if self.modo is ModoOse.RESPUESTA_INVALIDA:
            raise OseRespuestaInvalida("La OSE devolvió una respuesta que no es un CDR válido.")

        _, tipo, serie_numero = nombre_archivo.split("-", 2)
        tipo_comprobante = TipoComprobante(tipo)
        ahora = self._reloj.ahora()
        if self.modo is ModoOse.RECHAZO:
            return Cdr("2335", "El documento electrónico ingresado ha sido alterado (rechazo simulado).", ahora)

        try:
            raiz = etree.fromstring(xml_firmado, parser_seguro())
            certificado = raiz.find(f".//{{{NAMESPACES['ds']}}}X509Certificate").text
            pem = f"-----BEGIN CERTIFICATE-----\n{certificado.strip()}\n-----END CERTIFICATE-----\n"
            XMLVerifier().verify(raiz, x509_cert=pem, expect_references=1)
        except (InvalidSignature, InvalidInput, AttributeError):
            return Cdr("2335", "El documento electrónico ingresado ha sido alterado.", ahora)
        try:
            self._validador.validar(xml_firmado, tipo_comprobante)
        except XmlNoConformeXsd:
            return Cdr("0306", "No se puede leer (parsear) el archivo XML.", ahora)

        return Cdr("0", f"La {tipo_comprobante.descripcion} numero {serie_numero}, ha sido aceptada", ahora)
