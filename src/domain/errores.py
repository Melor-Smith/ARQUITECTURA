"""Errores del dominio.

Toda violación de una regla de negocio o normativa se expresa con una subclase de
``ErrorDominio``. El dominio no conoce HTTP: es el adaptador web quien traduce
``ErrorDominio`` a 422 y ``ConflictoDominio`` a 409.
"""

from __future__ import annotations


class ErrorDominio(Exception):
    """Regla de negocio o normativa SUNAT incumplida."""

    codigo: str = "ERR-REGLA-NEGOCIO"

    def __init__(self, mensaje: str, *, codigo: str | None = None, campo: str | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo
        if codigo is not None:
            self.codigo = codigo


class ConflictoDominio(ErrorDominio):
    """La operación es válida en sí misma, pero choca con el estado actual del agregado."""

    codigo = "ERR-CONFLICTO"


class RucInvalido(ErrorDominio):
    codigo = "ERR-SUNAT-RUC"


class DocumentoIdentidadInvalido(ErrorDominio):
    codigo = "ERR-SUNAT-DOC-IDENTIDAD"


class SerieInvalida(ErrorDominio):
    codigo = "ERR-SUNAT-SERIE"


class CorrelativoInvalido(ErrorDominio):
    codigo = "ERR-SUNAT-CORRELATIVO"


class ReglaComprobanteIncumplida(ErrorDominio):
    codigo = "ERR-SUNAT-COMPROBANTE"


class ReglaTributariaIncumplida(ErrorDominio):
    codigo = "ERR-SUNAT-TRIBUTO"


class ConfiguracionIscInvalida(ErrorDominio):
    codigo = "ERR-SUNAT-CAT08"


class UnidadMedidaInvalida(ErrorDominio):
    codigo = "ERR-SUNAT-CAT03"


class SaldoInsuficiente(ErrorDominio):
    codigo = "ERR-KARDEX-SALDO-INSUFICIENTE"


class FichaLegadoInvalida(ErrorDominio):
    codigo = "ERR-LEGADO-FICHA"
