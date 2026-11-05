"""Errores de la capa de aplicación (no son reglas de negocio)."""

from __future__ import annotations


class ErrorAplicacion(Exception):
    codigo: str = "ERR-APLICACION"

    def __init__(self, mensaje: str, *, codigo: str | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        if codigo is not None:
            self.codigo = codigo


class RecursoNoEncontrado(ErrorAplicacion):
    codigo = "ERR-NO-ENCONTRADO"


class Conflicto(ErrorAplicacion):
    """El recurso ya existe o la clave de idempotencia se reutilizó con otro contenido."""

    codigo = "ERR-CONFLICTO"


class OseNoDisponible(ErrorAplicacion):
    codigo = "ERR-OSE-NO-DISPONIBLE"

    def __init__(self, mensaje: str, *, reintentar_en_segundos: int = 60) -> None:
        super().__init__(mensaje)
        self.reintentar_en_segundos = reintentar_en_segundos


class OseRespuestaInvalida(ErrorAplicacion):
    codigo = "ERR-OSE-RESPUESTA-INVALIDA"


class XmlNoConformeXsd(ErrorAplicacion):
    """El XML generado no valida contra UBL 2.1. Es un defecto interno, no del cliente."""

    codigo = "ERR-UBL-XSD"

    def __init__(self, mensaje: str, errores: list[str]) -> None:
        super().__init__(mensaje)
        self.errores = errores
