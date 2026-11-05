"""Puertos de salida (driven ports) del hexágono.

Los casos de uso dependen solo de estas interfaces. Las implementaciones concretas
(memoria, lxml/xsdata, signxml, OSE) están en ``src/adapters/outbound`` y se inyectan en
``src/bootstrap.py``.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from src.domain.catalogos import TipoComprobante
from src.domain.comprobante import Cdr, Comprobante
from src.domain.inventario import Homologacion, Kardex, MigracionLegado, MovimientoInventario, Producto
from src.domain.lotes import LoteMigracion
from src.domain.valores import Correlativo, Ruc, Serie


class Reloj(Protocol):
    def ahora(self) -> dt.datetime:
        """Fecha y hora actuales en la zona horaria de Perú (UTC-5)."""
        ...


class UnidadDeTrabajo(Protocol):
    def transaccion(self) -> AbstractContextManager[None]:
        """Agrupa lecturas y escrituras de varios repositorios de forma atómica."""
        ...


class SecuenciaCorrelativos(Protocol):
    def siguiente(self, ruc: Ruc, tipo: TipoComprobante, serie: Serie) -> Correlativo:
        """Reserva de forma atómica el siguiente correlativo de la serie. Nunca lo decide el cliente."""
        ...


class GeneradorIdentificadores(Protocol):
    def siguiente(self, prefijo: str) -> str: ...


class RepositorioComprobantes(Protocol):
    def agregar(self, comprobante: Comprobante) -> None:
        """Falla con ``Conflicto`` si ya existe un comprobante con el mismo tipo, serie y número."""
        ...

    def actualizar(self, comprobante: Comprobante) -> None: ...

    def obtener(self, tipo: TipoComprobante, serie_numero: str) -> Comprobante | None: ...

    def listar(self) -> Iterator[Comprobante]: ...

    def notas_de(self, referencia: Comprobante) -> list[Comprobante]: ...


@dataclass(frozen=True, slots=True)
class RegistroIdempotencia:
    huella: str
    tipo: TipoComprobante
    serie_numero: str


class RepositorioIdempotencia(Protocol):
    def obtener(self, clave: str) -> RegistroIdempotencia | None: ...

    def guardar(self, clave: str, registro: RegistroIdempotencia) -> None: ...


class RepositorioProductos(Protocol):
    def obtener(self, codigo: str) -> Producto | None: ...

    def homologar(self, texto_legado: str) -> Homologacion | None: ...


class RepositorioKardex(Protocol):
    def obtener(self, establecimiento: str, producto: Producto) -> Kardex: ...

    def guardar(self, kardex: Kardex) -> None: ...

    def movimientos(self) -> Iterator[MovimientoInventario]: ...


class RepositorioMigraciones(Protocol):
    def obtener(self, nro_documento: str) -> MigracionLegado | None: ...

    def guardar(self, migracion: MigracionLegado) -> None: ...


class RepositorioLotes(Protocol):
    """Guarda el resultado de cada lote de migración (auditoría del corte)."""

    def guardar(self, lote: LoteMigracion) -> None: ...

    def obtener(self, id_lote: str) -> LoteMigracion | None: ...


class GeneradorUBL(Protocol):
    def generar(self, comprobante: Comprobante) -> bytes:
        """Serializa el comprobante a XML UBL 2.1 a partir de clases derivadas del XSD."""
        ...


class ValidadorEsquemaUBL(Protocol):
    def validar(self, xml: bytes, tipo: TipoComprobante) -> None:
        """Valida contra el XSD oficial OASIS UBL 2.1; lanza ``XmlNoConformeXsd`` si falla."""
        ...


@dataclass(frozen=True, slots=True)
class DocumentoFirmado:
    xml: bytes
    digest_value: str  # ds:DigestValue en base64; es el "hash CPE" de la representación impresa


class FirmaDigital(Protocol):
    def firmar(self, xml: bytes) -> DocumentoFirmado:
        """Firma XMLDSig enveloped dentro de ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent."""
        ...


class ClienteOSE(Protocol):
    def enviar(self, nombre_archivo: str, xml_firmado: bytes) -> Cdr:
        """Envía el comprobante a la OSE/SUNAT y devuelve el CDR.

        Lanza ``OseNoDisponible`` (sin respuesta) u ``OseRespuestaInvalida`` (respuesta ilegible).
        """
        ...
