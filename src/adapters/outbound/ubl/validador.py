"""Adaptador ``ValidadorEsquemaUBL``: valida con lxml contra los XSD oficiales completos."""

from __future__ import annotations

import threading
from pathlib import Path

from lxml import etree

from src.adapters.outbound.ubl import DIRECTORIO_XSD
from src.application.errores import XmlNoConformeXsd
from src.domain.catalogos import TipoComprobante

_ESQUEMAS = {
    TipoComprobante.FACTURA: "UBL-Invoice-2.1.xsd",
    TipoComprobante.BOLETA: "UBL-Invoice-2.1.xsd",
    TipoComprobante.NOTA_CREDITO: "UBL-CreditNote-2.1.xsd",
    TipoComprobante.NOTA_DEBITO: "UBL-DebitNote-2.1.xsd",
}


def parser_seguro() -> etree.XMLParser:
    """Parser sin resolución de entidades ni acceso a red (previene XXE)."""
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


class ValidadorXsdLxml:
    def __init__(self, directorio_xsd: Path = DIRECTORIO_XSD) -> None:
        self._directorio = directorio_xsd
        self._cache: dict[str, etree.XMLSchema] = {}
        self._lock = threading.Lock()

    def _esquema(self, archivo: str) -> etree.XMLSchema:
        with self._lock:
            if archivo not in self._cache:
                ruta = self._directorio / "maindoc" / archivo
                self._cache[archivo] = etree.XMLSchema(etree.parse(str(ruta)))
            return self._cache[archivo]

    def validar(self, xml: bytes, tipo: TipoComprobante) -> None:
        esquema = self._esquema(_ESQUEMAS[tipo])
        try:
            documento = etree.fromstring(xml, parser_seguro())
        except etree.XMLSyntaxError as exc:
            raise XmlNoConformeXsd("El XML no está bien formado.", [str(exc)]) from exc
        # XMLSchema no es seguro entre hilos: se valida bajo el mismo lock.
        with self._lock:
            valido = esquema.validate(documento)
            errores = [f"línea {e.line}: {e.message}" for e in esquema.error_log]
        if not valido:
            raise XmlNoConformeXsd(f"El XML no valida contra {_ESQUEMAS[tipo]}.", errores)
