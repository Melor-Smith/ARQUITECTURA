"""Estructura de los TXT del PLE según el Anexo 2 de la RS 286-2009/SUNAT (PLE 5.0).

El layout del TXT no es un detalle de presentación: lo fija la norma. Cada campo tiene un
número, un tipo de dato, una longitud y una obligatoriedad, y el programa PLE rechaza el
archivo si alguno no cumple. Por eso la estructura vive en el dominio, como datos, y una
prueba la contrasta con el Excel oficial de SUNAT (``specs/ple/anexo2``).

Reglas generales del Anexo 2 que se aplican aquí:

* Campos separados por ``|``; cada línea termina con ``|`` (no hay cabecera).
* Fecha: ``DD/MM/AAAA``. Importe: hasta 12 enteros y 2 decimales, punto decimal, sin
  separador de miles; negativo como ``-#.##``. Tipo de cambio: ``#.###``.
* Texto: no admite ``|``, ``/`` ni ``\\``.
* Alfanumérico: letras, dígitos y ``( ) , . -``.
* Campo sin dato: vacío entre separadores (``||``), nunca un espacio.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from src.domain.catalogos import UnidadMedida
from src.domain.errores import ErrorDominio

SEPARADOR = "|"
FIN_DE_LINEA = "\r\n"


class TipoDato(Enum):
    NUMERICO = "Numérico"
    TEXTO = "Texto"
    ALFANUMERICO = "Alfanumérico"
    FECHA = "DD/MM/AAAA"
    IMPORTE = "Numérico (12 enteros, 2 decimales)"
    TIPO_CAMBIO = "Numérico (1 entero, 3 decimales)"


@dataclass(frozen=True, slots=True)
class Campo:
    numero: int
    atributo: str  # atributo de la fila del dominio que lo alimenta
    nombre: str
    tipo: TipoDato
    longitud_max: int  # para importes: dígitos enteros (12); para tipo de cambio: 1
    obligatorio: bool
    longitud_min: int = 0
    patron: str | None = None  # validación adicional del Anexo 2


@dataclass(frozen=True, slots=True)
class Inconsistencia:
    linea: int
    campo: int
    nombre: str
    valor: str
    motivo: str

    def __str__(self) -> str:
        return f"línea {self.linea}, campo {self.campo} ({self.nombre}) = '{self.valor}': {self.motivo}"


class EstructuraPleInvalida(ErrorDominio):
    codigo = "ERR-PLE-ESTRUCTURA"

    def __init__(self, libro: str, inconsistencias: Sequence[Inconsistencia]) -> None:
        detalle = "; ".join(str(i) for i in inconsistencias[:5])
        extra = f" (y {len(inconsistencias) - 5} más)" if len(inconsistencias) > 5 else ""
        super().__init__(f"El libro {libro} no cumple el Anexo 2 de la RS 286-2009: {detalle}{extra}.")
        self.inconsistencias = tuple(inconsistencias)


def _c(numero: int, atributo: str, nombre: str, tipo: TipoDato, longitud: int, obligatorio: bool,
       minimo: int = 0, patron: str | None = None) -> Campo:
    return Campo(numero, atributo, nombre, tipo, longitud, obligatorio, minimo, patron)


_N, _T, _A, _F, _I, _TC = (TipoDato.NUMERICO, TipoDato.TEXTO, TipoDato.ALFANUMERICO, TipoDato.FECHA,
                           TipoDato.IMPORTE, TipoDato.TIPO_CAMBIO)
_PERIODO = r"^\d{4}(0[1-9]|1[0-2])00$"
_ASIENTO = r"^[AMC]"
_SIN_AMPERSAND = r"^[^&]+$"

#: Formato 14.1: Registro de Ventas e Ingresos (35 campos; del 36 al 70 son de libre uso).
ESTRUCTURA_141: tuple[Campo, ...] = (
    _c(1, "periodo", "Periodo", _N, 8, True, 8, _PERIODO),
    _c(2, "cuo", "Código Único de la Operación (CUO)", _T, 40, True, 1, _SIN_AMPERSAND),
    _c(3, "correlativo_asiento", "Correlativo del asiento contable", _A, 10, True, 2, _ASIENTO),
    _c(4, "fecha_emision", "Fecha de emisión del comprobante", _F, 10, False),
    _c(5, "fecha_vencimiento", "Fecha de vencimiento o fecha de pago", _F, 10, False),
    _c(6, "tipo_comprobante", "Tipo de comprobante (tabla 10)", _N, 2, True, 2),
    _c(7, "serie", "Serie del comprobante", _A, 20, True, 1),
    _c(8, "numero", "Número del comprobante", _A, 20, True, 1),
    _c(9, "numero_final", "Número final (consolidado de tickets o boletas)", _N, 20, False),
    _c(10, "tipo_documento_cliente", "Tipo de documento de identidad del cliente (tabla 2)", _A, 1, False),
    _c(11, "numero_documento_cliente", "Número de documento de identidad del cliente", _A, 15, False),
    _c(12, "nombre_cliente", "Apellidos y nombres, denominación o razón social del cliente", _T, 100, False),
    _c(13, "valor_exportacion", "Valor facturado de la exportación", _I, 12, False),
    _c(14, "base_gravada", "Base imponible de la operación gravada", _I, 12, False),
    _c(15, "descuento_base_gravada", "Descuento de la base imponible", _I, 12, False),
    _c(16, "igv", "IGV y/o IPM", _I, 12, False),
    _c(17, "descuento_igv", "Descuento del IGV y/o IPM", _I, 12, False),
    _c(18, "importe_exonerado", "Importe total de la operación exonerada", _I, 12, False),
    _c(19, "importe_inafecto", "Importe total de la operación inafecta", _I, 12, False),
    _c(20, "isc", "Impuesto Selectivo al Consumo", _I, 12, False),
    _c(21, "base_ivap", "Base imponible de la operación gravada con el IVAP", _I, 12, False),
    _c(22, "ivap", "Impuesto a las Ventas del Arroz Pilado", _I, 12, False),
    _c(23, "icbper", "Impuesto al Consumo de las Bolsas de Plástico", _I, 12, False),
    _c(24, "otros_tributos", "Otros conceptos, tributos y cargos", _I, 12, False),
    _c(25, "importe_total", "Importe total del comprobante", _I, 12, False),
    _c(26, "moneda", "Código de la moneda (tabla 4)", _A, 3, False),
    _c(27, "tipo_cambio", "Tipo de cambio", _TC, 1, False),
    _c(28, "fecha_modificado", "Fecha de emisión del comprobante que se modifica", _F, 10, False),
    _c(29, "tipo_modificado", "Tipo del comprobante que se modifica", _N, 2, False),
    _c(30, "serie_modificado", "Serie del comprobante que se modifica o código de la dependencia aduanera",
       _A, 20, False),
    _c(31, "numero_modificado", "Número del comprobante que se modifica o número de la DUA", _A, 20, False),
    _c(32, "contrato", "Identificación del contrato o proyecto (colaboración empresarial)", _T, 12, False),
    _c(33, "error_tipo_cambio", "Error tipo 1: inconsistencia en el tipo de cambio", _N, 1, False),
    _c(34, "indicador_medio_pago", "Indicador de comprobante cancelado con medio de pago", _N, 1, False),
    _c(35, "estado", "Estado que identifica la oportunidad de la anotación", _N, 1, True, 1, r"^[01289]$"),
)

#: Formato 12.1: Registro del Inventario Permanente en Unidades Físicas (19 campos; 20 al 40 libres).
ESTRUCTURA_121: tuple[Campo, ...] = (
    _c(1, "periodo", "Periodo", _N, 8, True, 8, _PERIODO),
    _c(2, "cuo", "Código Único de la Operación (CUO)", _T, 40, True, 1, _SIN_AMPERSAND),
    _c(3, "correlativo_asiento", "Correlativo del asiento contable", _A, 10, True, 2, _ASIENTO),
    _c(4, "establecimiento", "Código de establecimiento anexo", _N, 7, True, 4),
    _c(5, "catalogo", "Código del catálogo utilizado (tabla 13)", _N, 1, True, 1),
    _c(6, "tipo_existencia", "Tipo de existencia (tabla 5)", _N, 2, True, 2),
    _c(7, "codigo_existencia", "Código propio de la existencia", _A, 24, True, 1),
    _c(8, "catalogo_internacional", "Código del catálogo internacional (tabla 13: UNSPSC o GTIN)", _N, 1, False,
       patron=r"^[1-8]$"),
    _c(9, "codigo_internacional", "Código de la existencia en el catálogo internacional", _N, 128, False),
    _c(10, "fecha_documento", "Fecha de emisión del documento", _F, 10, True),
    _c(11, "tipo_documento", "Tipo de documento (tabla 10)", _N, 2, True, 2),
    _c(12, "serie_documento", "Serie del documento", _A, 20, True, 1),
    _c(13, "numero_documento", "Número del documento", _A, 20, True, 1),
    _c(14, "tipo_operacion", "Tipo de operación (tabla 12)", _N, 2, True, 2),
    _c(15, "descripcion_existencia", "Descripción de la existencia", _T, 80, True, 1),
    _c(16, "unidad_medida", "Código de la unidad de medida (tabla 6)", _A, 3, True, 1),
    _c(17, "entrada", "Entradas de unidades físicas", _I, 12, True),
    _c(18, "salida", "Salidas de unidades físicas", _I, 12, True),
    _c(19, "estado", "Estado de la operación", _N, 1, True, 1, r"^[189]$"),
)

ESTRUCTURAS: dict[str, tuple[Campo, ...]] = {"140100": ESTRUCTURA_141, "120100": ESTRUCTURA_121}


# --- formato de cada valor ------------------------------------------------------------
_PROHIBIDOS_TEXTO = re.compile(r"[|/\\\r\n\t]+")
_NO_ALFANUMERICO = re.compile(r"[^A-Za-z0-9(),.\-]+")
_ESPACIOS = re.compile(r"\s+")
_DOS_DECIMALES = Decimal("0.01")
_TRES_DECIMALES = Decimal("0.001")


def _sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def formatear(campo: Campo, valor: object) -> str:
    """Convierte el valor del dominio al texto que exige el Anexo 2 para ese campo.

    Normaliza lo que la norma permite normalizar (redondeo, ``-0.00``, caracteres prohibidos
    del texto, longitud máxima del texto libre); lo que no se puede corregir sin inventar
    datos lo detecta ``validar_linea``.
    """
    if valor is None or valor == "":
        return ""
    if campo.tipo is TipoDato.FECHA:
        if not isinstance(valor, dt.date):
            raise TypeError(f"El campo {campo.numero} espera una fecha")
        return valor.strftime("%d/%m/%Y")
    if campo.tipo in (TipoDato.IMPORTE, TipoDato.TIPO_CAMBIO):
        if not isinstance(valor, Decimal):
            raise TypeError(f"El campo {campo.numero} espera un Decimal")
        escala = _TRES_DECIMALES if campo.tipo is TipoDato.TIPO_CAMBIO else _DOS_DECIMALES
        redondeado = valor.quantize(escala, rounding=ROUND_HALF_UP)
        return f"{redondeado.copy_abs() if redondeado.is_zero() else redondeado:f}"  # nunca "-0.00"
    texto = str(valor)
    if campo.tipo is TipoDato.TEXTO:
        limpio = _ESPACIOS.sub(" ", _PROHIBIDOS_TEXTO.sub(" ", texto)).strip()
        return limpio[: campo.longitud_max].rstrip()
    if campo.tipo is TipoDato.ALFANUMERICO:
        return _NO_ALFANUMERICO.sub("-", _sin_tildes(texto).strip()).strip("-")
    return texto.strip()


def valores(estructura: Sequence[Campo], fila: object) -> tuple[str, ...]:
    """Valores ya formateados de una fila, en el orden de la estructura."""
    return tuple(formatear(c, getattr(fila, c.atributo)) for c in estructura)


def linea_txt(estructura: Sequence[Campo], fila: object) -> str:
    return SEPARADOR.join(valores(estructura, fila)) + SEPARADOR


# --- validación -----------------------------------------------------------------------
_PATRONES_TIPO: dict[TipoDato, re.Pattern[str]] = {
    TipoDato.NUMERICO: re.compile(r"^\d+$"),
    TipoDato.FECHA: re.compile(r"^\d{2}/\d{2}/\d{4}$"),
    TipoDato.IMPORTE: re.compile(r"^-?\d{1,12}\.\d{2}$"),
    TipoDato.TIPO_CAMBIO: re.compile(r"^\d\.\d{3}$"),
    TipoDato.ALFANUMERICO: re.compile(r"^[A-Za-z0-9(),.\-]+$"),
    TipoDato.TEXTO: re.compile(r"^[^|/\\\r\n]+$"),
}


def validar_campo(campo: Campo, valor: str) -> str | None:
    """Motivo por el que el valor incumple el Anexo 2, o ``None`` si cumple."""
    if valor == "":
        return "es obligatorio" if campo.obligatorio else None
    if valor != valor.strip():
        return "no debe tener espacios al inicio ni al final"
    if not _PATRONES_TIPO[campo.tipo].match(valor):
        return f"no cumple el formato {campo.tipo.value}"
    if campo.tipo is TipoDato.FECHA:
        try:
            dt.datetime.strptime(valor, "%d/%m/%Y")
        except ValueError:
            return "no es una fecha válida"
    elif campo.tipo not in (TipoDato.IMPORTE, TipoDato.TIPO_CAMBIO):
        if len(valor) > campo.longitud_max:
            return f"supera la longitud máxima de {campo.longitud_max}"
        if len(valor) < campo.longitud_min:
            return f"no alcanza la longitud mínima de {campo.longitud_min}"
    if campo.patron and not re.search(campo.patron, valor):
        return f"no cumple la regla {campo.patron}"
    if campo.tipo is TipoDato.TIPO_CAMBIO and Decimal(valor) <= 0:
        return "debe ser positivo"
    return None


def validar_linea(estructura: Sequence[Campo], linea: str, numero_linea: int = 1) -> list[Inconsistencia]:
    """Valida una línea del TXT tal como la leería el programa PLE."""
    if not linea.endswith(SEPARADOR):
        return [Inconsistencia(numero_linea, 0, "línea", linea[-20:], "debe terminar con el separador '|'")]
    partes = linea[:-1].split(SEPARADOR)
    if len(partes) != len(estructura):
        return [Inconsistencia(numero_linea, 0, "línea", str(len(partes)),
                               f"tiene {len(partes)} campos y la estructura exige {len(estructura)}")]
    return [
        Inconsistencia(numero_linea, c.numero, c.nombre, v, motivo)
        for c, v in zip(estructura, partes, strict=True)
        if (motivo := validar_campo(c, v)) is not None
    ]


# --- reglas entre campos (columna "Observaciones" del Anexo 2) ----------------------
_TIPOS_NOTA = {"07", "08", "87", "88"}


def _fin_del_mes_siguiente(periodo: str) -> dt.date:
    anio, mes = int(periodo[:4]), int(periodo[4:6])
    anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    return dt.date(anio, mes, calendar.monthrange(anio, mes)[1])


def _fecha(valor: str) -> dt.date:
    return dt.datetime.strptime(valor, "%d/%m/%Y").date()


def _reglas_141(v: dict[int, str], n: int) -> list[Inconsistencia]:
    e = ESTRUCTURA_141
    errores: list[Inconsistencia] = []

    def falla(campo: int, motivo: str) -> None:
        errores.append(Inconsistencia(n, campo, e[campo - 1].nombre, v[campo], motivo))

    if v[35] != "2" and not v[4]:
        falla(4, "es obligatoria salvo en comprobantes anulados (campo 35 = 2)")
    if v[5] and _fecha(v[5]) > _fin_del_mes_siguiente(v[1]):
        falla(5, "no puede ser posterior al mes siguiente del periodo informado")
    if v[6] in _TIPOS_NOTA and v[35] != "2":
        for campo in (28, 29, 30, 31):
            if not v[campo]:
                falla(campo, "es obligatorio en notas de crédito y débito")
    if v[26] and not v[27]:
        falla(27, "es obligatorio cuando se informa la moneda (campo 26)")
    if v[10] == "0" and v[6] in {"03", "12"}:
        falla(10, "el PLE no acepta el valor 0; si el cliente no se identifica, el campo va vacío")
    if v[9] and v[6] not in {"00", "03", "12", "13", "87"}:
        falla(9, "solo se usa para tipos 00, 03, 12, 13 y 87")
    if v[6] in {"01", "03", "07", "08", "12", "87", "88"} and not v[23]:
        falla(23, "es obligatorio para este tipo de comprobante (por defecto 0.00)")
    return errores


def _reglas_121(v: dict[int, str], n: int) -> list[Inconsistencia]:
    e = ESTRUCTURA_121
    errores: list[Inconsistencia] = []

    def falla(campo: int, motivo: str) -> None:
        errores.append(Inconsistencia(n, campo, e[campo - 1].nombre, v[campo], motivo))

    if v[17] and v[18] and Decimal(v[17]) != 0 and Decimal(v[18]) != 0:
        falla(18, "entradas (17) y salidas (18) son excluyentes")
    if v[9] and not v[8]:
        falla(8, "es obligatorio cuando se informa el código internacional (campo 9)")
    if v[16] not in _UNIDADES_UNECE:
        falla(16, "el valor no se encontró en la tabla de parámetros (unidades UN/ECE, p. ej. KGM o NIU)")
    if v[14] in {"01", "02", "03", "04", "05", "06"} and v[11] == "00":
        falla(11, "tipo de documento no válido para el tipo de operación efectuada (14 = 01 a 06 exige "
                  "comprobante o guía, no '00')")
    return errores


_UNIDADES_UNECE = frozenset(u.value for u in UnidadMedida)
_REGLAS = {"140100": _reglas_141, "120100": _reglas_121}


def validar_filas(identificador: str, filas: Sequence[object]) -> list[Inconsistencia]:
    """Todas las inconsistencias de un libro: estructura de cada campo y reglas entre campos."""
    estructura = ESTRUCTURAS[identificador]
    inconsistencias: list[Inconsistencia] = []
    for n, fila in enumerate(filas, start=1):
        linea = linea_txt(estructura, fila)
        de_la_linea = validar_linea(estructura, linea, n)
        if not de_la_linea:
            por_numero = dict(zip((c.numero for c in estructura), linea[:-1].split(SEPARADOR), strict=True))
            de_la_linea = _REGLAS[identificador](por_numero, n)
        inconsistencias.extend(de_la_linea)
    return inconsistencias


def contenido_txt(identificador: str, filas: Sequence[object]) -> str:
    """Contenido del TXT: una línea por fila, ``|`` final y CRLF. Si alguna fila incumple el
    Anexo 2, no se genera un archivo que el PLE rechazaría: se levanta ``EstructuraPleInvalida``."""
    inconsistencias = validar_filas(identificador, filas)
    if inconsistencias:
        raise EstructuraPleInvalida(identificador, inconsistencias)
    estructura = ESTRUCTURAS[identificador]
    return "".join(linea_txt(estructura, f) + FIN_DE_LINEA for f in filas)
