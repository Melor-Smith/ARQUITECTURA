"""Importe en letras para la leyenda 1000 del comprobante (Catálogo 52).

Ejemplo: ``359.90`` en PEN → ``TRESCIENTOS CINCUENTA Y NUEVE CON 90/100 SOLES``.
"""

from __future__ import annotations

from decimal import Decimal

from src.domain.catalogos import Moneda
from src.domain.errores import ErrorDominio
from src.domain.tributos import redondear

_UNIDADES = ("CERO", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE", "DIEZ",
             "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE",
             "VEINTE", "VEINTIUNO", "VEINTIDÓS", "VEINTITRÉS", "VEINTICUATRO", "VEINTICINCO", "VEINTISÉIS",
             "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE")
_DECENAS = {3: "TREINTA", 4: "CUARENTA", 5: "CINCUENTA", 6: "SESENTA", 7: "SETENTA", 8: "OCHENTA", 9: "NOVENTA"}
_CENTENAS = {1: "CIENTO", 2: "DOSCIENTOS", 3: "TRESCIENTOS", 4: "CUATROCIENTOS", 5: "QUINIENTOS",
             6: "SEISCIENTOS", 7: "SETECIENTOS", 8: "OCHOCIENTOS", 9: "NOVECIENTOS"}
_NOMBRE_MONEDA = {Moneda.PEN: "SOLES", Moneda.USD: "DÓLARES AMERICANOS"}
_MAXIMO = Decimal("999999999999.99")


def _hasta_999(n: int) -> str:
    if n < 30:
        return _UNIDADES[n]
    if n < 100:
        decena, unidad = divmod(n, 10)
        return _DECENAS[decena] + (f" Y {_UNIDADES[unidad]}" if unidad else "")
    if n == 100:
        return "CIEN"
    centena, resto = divmod(n, 100)
    return _CENTENAS[centena] + (f" {_hasta_999(resto)}" if resto else "")


def _apocopar(texto: str) -> str:
    """Delante de MIL o MILLONES: UNO → UN y VEINTIUNO → VEINTIÚN."""
    if texto.endswith("VEINTIUNO"):
        return texto[:-9] + "VEINTIÚN"
    if texto.endswith("UNO"):
        return texto[:-3] + "UN"
    return texto


def entero_en_letras(n: int) -> str:
    if n < 0:
        raise ValueError("Solo se convierten importes no negativos.")
    if n < 1000:
        return _hasta_999(n)
    if n < 1_000_000:
        miles, resto = divmod(n, 1000)
        cabeza = "MIL" if miles == 1 else f"{_apocopar(_hasta_999(miles))} MIL"
        return cabeza + (f" {_hasta_999(resto)}" if resto else "")
    millones, resto = divmod(n, 1_000_000)
    cabeza = "UN MILLÓN" if millones == 1 else f"{_apocopar(entero_en_letras(millones))} MILLONES"
    return cabeza + (f" {entero_en_letras(resto)}" if resto else "")


def importe_en_letras(importe: Decimal, moneda: Moneda) -> str:
    importe = redondear(importe)
    if importe < 0 or importe > _MAXIMO:
        raise ErrorDominio(f"No se puede expresar en letras el importe {importe}.", codigo="ERR-IMPORTE-LETRAS")
    entero = int(importe)
    centimos = int((importe - entero) * 100)
    return f"{entero_en_letras(entero)} CON {centimos:02d}/100 {_NOMBRE_MONEDA[moneda]}"
