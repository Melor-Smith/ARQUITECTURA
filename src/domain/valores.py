"""Objetos de valor: inmutables, se validan al construirse y se comparan por valor."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.domain.catalogos import TipoDocumentoIdentidad
from src.domain.errores import (
    CorrelativoInvalido,
    DocumentoIdentidadInvalido,
    RucInvalido,
    SerieInvalida,
)

_PREFIJOS_RUC = frozenset({"10", "15", "16", "17", "20"})
_PESOS_RUC = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def digito_verificador_ruc(primeros_diez: str) -> int:
    """Módulo 11 de SUNAT sobre los 10 primeros dígitos del RUC."""
    suma = sum(int(d) * p for d, p in zip(primeros_diez, _PESOS_RUC, strict=True))
    resto = 11 - (suma % 11)
    return {10: 0, 11: 1}.get(resto, resto)


@dataclass(frozen=True, slots=True)
class Ruc:
    """RUC de 11 dígitos con prefijo válido (10, 15, 16, 17 o 20) y dígito de control."""

    valor: str

    def __post_init__(self) -> None:
        v = self.valor
        if not (len(v) == 11 and v.isdigit()):
            raise RucInvalido(f"El RUC '{v}' debe tener exactamente 11 dígitos numéricos.", campo="ruc")
        if v[:2] not in _PREFIJOS_RUC:
            raise RucInvalido(
                f"El RUC '{v}' debe iniciar con 10, 15, 16, 17 o 20.", campo="ruc"
            )
        if int(v[10]) != digito_verificador_ruc(v[:10]):
            raise RucInvalido(
                f"El RUC '{v}' no supera la validación del dígito verificador (módulo 11).",
                campo="ruc",
            )

    def __str__(self) -> str:
        return self.valor


_REGLAS_DOCUMENTO: dict[TipoDocumentoIdentidad, tuple[re.Pattern[str], str]] = {
    TipoDocumentoIdentidad.DNI: (re.compile(r"^\d{8}$"), "8 dígitos"),
    TipoDocumentoIdentidad.CARNET_EXTRANJERIA: (re.compile(r"^[A-Z0-9]{1,12}$"), "hasta 12 caracteres alfanuméricos"),
    TipoDocumentoIdentidad.PASAPORTE: (re.compile(r"^[A-Z0-9]{1,12}$"), "hasta 12 caracteres alfanuméricos"),
    TipoDocumentoIdentidad.CEDULA_DIPLOMATICA: (re.compile(r"^[A-Z0-9]{1,15}$"), "hasta 15 caracteres alfanuméricos"),
    TipoDocumentoIdentidad.NO_DOMICILIADO: (re.compile(r"^[A-Z0-9-]{1,15}$"), "hasta 15 caracteres"),
}


@dataclass(frozen=True, slots=True)
class DocumentoIdentidad:
    """Tipo (Catálogo 06) y número del documento del adquiriente."""

    tipo: TipoDocumentoIdentidad
    numero: str

    def __post_init__(self) -> None:
        if self.tipo is TipoDocumentoIdentidad.RUC:
            Ruc(self.numero)
            return
        patron, descripcion = _REGLAS_DOCUMENTO[self.tipo]
        if not patron.match(self.numero):
            raise DocumentoIdentidadInvalido(
                f"El documento tipo {self.tipo.value} ({self.tipo.descripcion}) debe tener {descripcion}; "
                f"se recibió '{self.numero}'.",
                campo="cliente.numero_documento",
            )

    @property
    def es_ruc(self) -> bool:
        return self.tipo is TipoDocumentoIdentidad.RUC

    @property
    def es_anonimo(self) -> bool:
        return self.tipo is TipoDocumentoIdentidad.NO_DOMICILIADO


_PATRON_SERIE = re.compile(r"^[FB][A-Z0-9]{3}$")
CORRELATIVO_MAXIMO = 99_999_999


@dataclass(frozen=True, slots=True)
class Serie:
    """Serie alfanumérica de 4 caracteres: F (facturas y sus notas) o B (boletas y sus notas)."""

    valor: str

    def __post_init__(self) -> None:
        if not _PATRON_SERIE.match(self.valor):
            raise SerieInvalida(
                f"La serie '{self.valor}' no cumple el formato SUNAT ^[FB][A-Z0-9]{{3}}$.", campo="serie"
            )

    @property
    def letra(self) -> str:
        return self.valor[0]

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True, slots=True, order=True)
class Correlativo:
    """Número correlativo entero entre 1 y 99 999 999. Lo asigna siempre el servidor."""

    valor: int

    def __post_init__(self) -> None:
        if isinstance(self.valor, bool) or not isinstance(self.valor, int):
            raise CorrelativoInvalido("El correlativo debe ser un número entero.")
        if not 1 <= self.valor <= CORRELATIVO_MAXIMO:
            raise CorrelativoInvalido(
                f"El correlativo {self.valor} está fuera del rango permitido (1 a {CORRELATIVO_MAXIMO:,})."
            )

    def siguiente(self) -> Correlativo:
        return Correlativo(self.valor + 1)

    def __str__(self) -> str:
        return str(self.valor)


_PATRON_NUMERO = re.compile(r"^([FB][A-Z0-9]{3})-(\d{1,8})$")


@dataclass(frozen=True, slots=True)
class NumeroComprobante:
    """Serie + correlativo. Solo se unen al serializar (``cbc:ID``), por ejemplo ``F001-1``."""

    serie: Serie
    correlativo: Correlativo

    @classmethod
    def parsear(cls, texto: str) -> NumeroComprobante:
        """Acepta ``F001-1`` o ``F001-00000001``; ambos representan el mismo número."""
        coincidencia = _PATRON_NUMERO.match(texto)
        if not coincidencia:
            raise SerieInvalida(
                f"'{texto}' no cumple el formato SUNAT [FB][A-Z0-9]{{3}}-[0-9]{{1,8}}.", campo="serie_numero"
            )
        return cls(Serie(coincidencia.group(1)), Correlativo(int(coincidencia.group(2))))

    def __str__(self) -> str:
        return f"{self.serie}-{self.correlativo}"
