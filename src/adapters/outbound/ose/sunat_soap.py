"""Adaptador ``ClienteOSE`` real: servicio SOAP ``sendBill`` de SUNAT (SEE - Del contribuyente).

Implementa el mismo puerto que ``OseSimulada``; ``src/bootstrap.py`` elige uno u otro por
configuración (``ABC_SUNAT_ENDPOINT``). Ningún caso de uso cambia.

Protocolo (Manual del programador SEE, servicio ``billService``):

1. El XML firmado va comprimido en un ZIP ``RUC-TT-SERIE-NUMERO.zip`` que contiene
   ``RUC-TT-SERIE-NUMERO.xml``, codificado en Base64 dentro de ``<ser:sendBill>``.
2. La autenticación es WS-Security ``UsernameToken``: usuario = RUC + usuario SOL.
   En el entorno beta el usuario SOL es ``MODDATOS`` y la clave ``moddatos``.
3. Si SUNAT procesa el comprobante responde ``applicationResponse``: un ZIP con el CDR
   ``R-RUC-TT-SERIE-NUMERO.xml`` (``cbc:ResponseCode``, ``cbc:Description``, ``cbc:Note``).
4. Si lo rechaza responde un SOAP Fault cuyo ``faultcode`` termina en el código del
   catálogo de errores (p. ej. ``soap-env:Client.3277``).

Traducción a la aplicación:

* CDR o rechazo 2000-3999 → ``Cdr`` (el dominio decide el estado).
* Excepciones de servicio (0100, 0109, 0130-0138, 0200) y fallas de red/HTTP →
  ``OseNoDisponible``: el comprobante queda pendiente y se reintenta (202).
* Otras excepciones 0100-1999 (credenciales, nombre de archivo, formato) → ``Cdr`` con
  ese código: el dominio lo reconoce como excepción y la aplicación responde 502.
* Respuesta que no es ni CDR ni Fault → ``OseRespuestaInvalida`` (502).
"""

from __future__ import annotations

import base64
import io
import re
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from xml.sax.saxutils import escape

from lxml import etree

from src.adapters.outbound.ubl.validador import parser_seguro
from src.application.errores import OseNoDisponible, OseRespuestaInvalida
from src.application.puertos import Reloj
from src.domain.comprobante import Cdr

#: Entorno de pruebas de SUNAT: acepta certificados autofirmados y no tiene efecto tributario.
ENDPOINT_BETA = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"
#: Producción. Exige usuario SOL secundario y certificado digital reales.
ENDPOINT_PRODUCCION = "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService"
USUARIO_BETA, CLAVE_BETA = "MODDATOS", "moddatos"

_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_WSSE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"


@dataclass(frozen=True, slots=True)
class RespuestaHttp:
    estado: int
    cuerpo: bytes


#: (url, cuerpo, cabeceras, timeout) -> respuesta. Inyectable para probar sin red.
Transporte = Callable[[str, bytes, dict[str, str], float], RespuestaHttp]


def transporte_urllib(url: str, cuerpo: bytes, cabeceras: dict[str, str], timeout: float) -> RespuestaHttp:
    """Transporte por defecto (biblioteca estándar). Los errores de red suben como ``OSError``."""
    solicitud = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method="POST")
    try:
        with urllib.request.urlopen(solicitud, timeout=timeout) as respuesta:
            return RespuestaHttp(respuesta.status, respuesta.read())
    except urllib.error.HTTPError as error:  # SUNAT devuelve los SOAP Fault con HTTP 500
        return RespuestaHttp(error.code, error.read())


#: Excepciones del catálogo de errores en las que SUNAT no pudo atender ("El sistema no puede
#: responder su solicitud..."): 0100, 0109, 0130-0138 y 0200. Son reintentables. Las demás
#: (credenciales 0101-0113, archivo 0150-0161, formato) se deben corregir antes de reenviar.
_EXCEPCIONES_DE_SERVICIO = frozenset({100, 109, *range(130, 139), 200})


def _codigo_excepcion_de_servicio(codigo: int) -> bool:
    return codigo in _EXCEPCIONES_DE_SERVICIO


class ClienteSunatSoap:
    def __init__(
        self,
        *,
        ruc: str,
        reloj: Reloj,
        endpoint: str = ENDPOINT_BETA,
        usuario_sol: str = USUARIO_BETA,
        clave_sol: str = CLAVE_BETA,
        timeout_segundos: float = 60.0,
        transporte: Transporte = transporte_urllib,
    ) -> None:
        self._ruc = ruc
        self._reloj = reloj
        self._endpoint = endpoint
        self._usuario = f"{ruc}{usuario_sol}"
        self._clave = clave_sol
        self._timeout = timeout_segundos
        self._transporte = transporte

    # --- solicitud ---------------------------------------------------------------------
    @staticmethod
    def comprimir(nombre_archivo: str, xml_firmado: bytes) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archivo:
            archivo.writestr(f"{nombre_archivo}.xml", xml_firmado)
        return buffer.getvalue()

    def sobre_soap(self, nombre_archivo: str, xml_firmado: bytes) -> bytes:
        contenido = base64.b64encode(self.comprimir(nombre_archivo, xml_firmado)).decode("ascii")
        return (
            f'<soapenv:Envelope xmlns:soapenv="{_SOAP}" xmlns:ser="http://service.sunat.gob.pe" '
            f'xmlns:wsse="{_WSSE}"><soapenv:Header><wsse:Security><wsse:UsernameToken>'
            f"<wsse:Username>{escape(self._usuario)}</wsse:Username>"
            f"<wsse:Password>{escape(self._clave)}</wsse:Password>"
            f"</wsse:UsernameToken></wsse:Security></soapenv:Header><soapenv:Body><ser:sendBill>"
            f"<fileName>{escape(nombre_archivo)}.zip</fileName><contentFile>{contenido}</contentFile>"
            f"</ser:sendBill></soapenv:Body></soapenv:Envelope>"
        ).encode()

    # --- puerto ClienteOSE -------------------------------------------------------------
    def enviar(self, nombre_archivo: str, xml_firmado: bytes) -> Cdr:
        if not nombre_archivo.startswith(f"{self._ruc}-"):
            raise OseRespuestaInvalida(f"El archivo {nombre_archivo} no pertenece al RUC {self._ruc}.")
        cabeceras = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "urn:sendBill"}
        try:
            respuesta = self._transporte(self._endpoint, self.sobre_soap(nombre_archivo, xml_firmado),
                                         cabeceras, self._timeout)
        except OSError as error:  # incluye URLError, timeout y conexión rechazada
            raise OseNoDisponible(f"SUNAT no respondió: {error}.", reintentar_en_segundos=120) from error
        return self.interpretar(respuesta)

    # --- respuesta ---------------------------------------------------------------------
    def interpretar(self, respuesta: RespuestaHttp) -> Cdr:
        try:
            sobre = etree.fromstring(respuesta.cuerpo, parser_seguro())
        except etree.XMLSyntaxError:
            if respuesta.estado in (401, 429) or respuesta.estado >= 500:
                raise OseNoDisponible(f"SUNAT respondió HTTP {respuesta.estado}.", reintentar_en_segundos=60) from None
            raise OseRespuestaInvalida(f"SUNAT respondió HTTP {respuesta.estado} sin un sobre SOAP.") from None

        cdr_zip = sobre.findtext(".//applicationResponse")
        if cdr_zip:
            return self._leer_cdr(base64.b64decode(cdr_zip))
        falla = sobre.find(f".//{{{_SOAP}}}Fault")
        if falla is not None:
            return self._leer_falla(falla.findtext("faultcode") or "", falla.findtext("faultstring") or "")
        raise OseRespuestaInvalida("La respuesta de SUNAT no contiene CDR ni SOAP Fault.")

    def _leer_cdr(self, contenido_zip: bytes) -> Cdr:
        try:
            with zipfile.ZipFile(io.BytesIO(contenido_zip)) as archivo:
                # El ZIP del CDR trae además una carpeta "dummy/" vacía.
                [nombre] = [n for n in archivo.namelist() if n.startswith("R-") and n.endswith(".xml")]
                cdr = etree.fromstring(archivo.read(nombre), parser_seguro())
        except (zipfile.BadZipFile, ValueError, etree.XMLSyntaxError) as error:
            raise OseRespuestaInvalida("SUNAT devolvió un CDR ilegible.") from error
        codigo = cdr.findtext(f".//{{{_CBC}}}ResponseCode")
        if codigo is None:
            raise OseRespuestaInvalida("El CDR no tiene cbc:ResponseCode.")
        notas = tuple(n.text or "" for n in cdr.iter(f"{{{_CBC}}}Note"))
        return Cdr(codigo.strip(), cdr.findtext(f".//{{{_CBC}}}Description") or "", self._reloj.ahora(), notas)

    def _leer_falla(self, faultcode: str, faultstring: str) -> Cdr:
        encontrado = re.search(r"(\d{4})$", faultcode.strip()) or re.match(r"\s*(\d{4})\b", faultstring)
        if encontrado is None:
            raise OseRespuestaInvalida(f"SOAP Fault sin código del catálogo de errores: {faultcode} {faultstring}")
        codigo = encontrado.group(1)
        if _codigo_excepcion_de_servicio(int(codigo)):
            raise OseNoDisponible(f"SUNAT {codigo}: {faultstring}", reintentar_en_segundos=120)
        return Cdr(codigo, faultstring.split(" - Detalle:")[0].strip(), self._reloj.ahora())
