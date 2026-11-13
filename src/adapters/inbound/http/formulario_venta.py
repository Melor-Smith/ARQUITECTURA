"""Formulario "Registrar venta": traduce los campos HTML al comando ``GenerarXmlVentaCmd``.

Es el equivalente, para la vista web, de lo que hace ``traduccion.py`` con el JSON de la API:
solo convierte texto en tipos del dominio (``Decimal``, catálogos SUNAT). No calcula impuestos ni
valida reglas de negocio; eso lo hace el dominio y sus errores vuelven al formulario.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import TypeVar
from urllib.parse import parse_qs

from src.application.comandos import ClienteCmd, GenerarXmlVentaCmd, LineaCmd
from src.domain.catalogos import AfectacionIGV, TipoComprobante, TipoDocumentoIdentidad, UnidadMedida

MAXIMO_LINEAS = 20
MAXIMO_BYTES = 32_000

#: Opciones que ofrece el formulario. Exportación (40) queda fuera: cambia el tipo de operación (Cat. 51).
TIPOS = (TipoComprobante.FACTURA, TipoComprobante.BOLETA)
DOCUMENTOS = (TipoDocumentoIdentidad.RUC, TipoDocumentoIdentidad.DNI, TipoDocumentoIdentidad.CARNET_EXTRANJERIA,
              TipoDocumentoIdentidad.PASAPORTE, TipoDocumentoIdentidad.NO_DOMICILIADO)
AFECTACIONES = (AfectacionIGV.GRAVADO_ONEROSA, AfectacionIGV.EXONERADO_ONEROSA, AfectacionIGV.INAFECTO_ONEROSA)
UNIDADES = tuple(UnidadMedida)

E = TypeVar("E", bound=Enum)

_LIMITES = {"descripcion": 500, "nombre": 200, "direccion": 250}


class ErrorFormulario(Exception):
    """Un campo no se pudo convertir (número mal escrito, código fuera del catálogo)."""

    codigo = "ERR-FORMULARIO"

    def __init__(self, mensaje: str, campo: str | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


def serie_aleatoria(tipo: TipoComprobante = TipoComprobante.FACTURA) -> str:
    """Serie nueva (F o B + 3 caracteres). El OSE-DEMO es compartido: repetir F001-1 da el error 1033."""
    letra = "B" if tipo is TipoComprobante.BOLETA else "F"
    return letra + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(3))


@dataclass
class LineaFormulario:
    descripcion: str = ""
    unidad: str = UnidadMedida.UNIDAD.value
    cantidad: str = ""
    valor_unitario: str = ""
    afectacion: str = AfectacionIGV.GRAVADO_ONEROSA.value

    @property
    def vacia(self) -> bool:
        return not (self.descripcion.strip() or self.cantidad.strip() or self.valor_unitario.strip())


@dataclass
class FormularioVenta:
    tipo: str = TipoComprobante.FACTURA.value
    serie: str = ""
    cliente_tipo: str = TipoDocumentoIdentidad.RUC.value
    cliente_numero: str = ""
    cliente_nombre: str = ""
    cliente_direccion: str = ""
    lineas: list[LineaFormulario] = field(default_factory=list)
    firmar: bool = False

    @classmethod
    def caso_de_estudio(cls) -> FormularioVenta:
        """La venta de ejemplo: una motocicleta de S/ 5 000.00 con IGV (4 237.29 + 762.71)."""
        return cls(
            serie=serie_aleatoria(),
            cliente_numero="20123456786",
            cliente_nombre="DISTRIBUIDORA DE ABARROTES EL SOL S.A.C.",
            cliente_direccion="JR. COMERCIO 123, LIMA",
            lineas=[LineaFormulario("Motocicleta 150 cc para reparto", UnidadMedida.UNIDAD.value, "1", "4237.29")],
        )

    @classmethod
    def desde_cuerpo(cls, cuerpo: str) -> FormularioVenta:
        """Lee un cuerpo ``application/x-www-form-urlencoded`` (los campos de línea se repiten)."""
        datos = parse_qs(cuerpo, keep_blank_values=True, max_num_fields=MAXIMO_LINEAS * 5 + 20)

        def uno(nombre: str) -> str:
            return datos.get(nombre, [""])[0].strip()

        columnas = [datos.get(n, []) for n in ("descripcion", "unidad", "cantidad", "valor_unitario", "afectacion")]
        filas = max((len(c) for c in columnas), default=0)
        lineas = [
            LineaFormulario(*(c[i].strip() if i < len(c) else "" for c in columnas))
            for i in range(filas)
        ]
        return cls(
            tipo=uno("tipo"), serie=uno("serie").upper(), cliente_tipo=uno("cliente_tipo"),
            cliente_numero=uno("cliente_numero").upper(), cliente_nombre=uno("cliente_nombre"),
            cliente_direccion=uno("cliente_direccion"),
            lineas=[ln for ln in lineas if not ln.vacia], firmar=uno("firmar") == "si",
        )

    def comando(self) -> GenerarXmlVentaCmd:
        if not self.lineas:
            raise ErrorFormulario("Registre al menos un producto.", "lineas")
        if len(self.lineas) > MAXIMO_LINEAS:
            raise ErrorFormulario(f"Se admiten hasta {MAXIMO_LINEAS} productos por venta.", "lineas")
        _largo(self.cliente_nombre, "nombre", "cliente.nombre")
        _largo(self.cliente_direccion, "direccion", "cliente.direccion")
        return GenerarXmlVentaCmd(
            tipo=_catalogo(TipoComprobante, self.tipo, TIPOS, "tipo_comprobante", "Tipo de comprobante"),
            serie=self.serie,
            cliente=ClienteCmd(
                _catalogo(TipoDocumentoIdentidad, self.cliente_tipo, DOCUMENTOS, "cliente.tipo_documento",
                          "Tipo de documento"),
                self.cliente_numero, self.cliente_nombre, self.cliente_direccion or None,
            ),
            lineas=tuple(self._linea(i, ln) for i, ln in enumerate(self.lineas)),
            incluir_firma=self.firmar,
        )

    @staticmethod
    def _linea(i: int, ln: LineaFormulario) -> LineaCmd:
        campo = f"lineas[{i}]"
        _largo(ln.descripcion, "descripcion", f"{campo}.descripcion")
        return LineaCmd(
            descripcion=ln.descripcion,
            unidad_medida=_catalogo(UnidadMedida, ln.unidad, UNIDADES, f"{campo}.unidad_medida", "Unidad"),
            cantidad=_decimal(ln.cantidad, f"{campo}.cantidad", f"La cantidad del producto {i + 1}"),
            valor_unitario=_decimal(ln.valor_unitario, f"{campo}.valor_unitario",
                                    f"El valor unitario del producto {i + 1}"),
            afectacion_igv=_catalogo(AfectacionIGV, ln.afectacion, AFECTACIONES, f"{campo}.afectacion_igv",
                                     "Afectación del IGV"),
        )


def _largo(valor: str, tipo: str, campo: str) -> None:
    if len(valor) > _LIMITES[tipo]:
        raise ErrorFormulario(f"El texto admite hasta {_LIMITES[tipo]} caracteres.", campo)


def _decimal(texto: str, campo: str, nombre: str) -> Decimal:
    try:
        valor = Decimal(texto.replace(",", "."))
    except InvalidOperation:
        raise ErrorFormulario(f"{nombre} debe ser un número (por ejemplo 4237.29).", campo) from None
    exponente = valor.as_tuple().exponent
    if not isinstance(exponente, int) or exponente < -10:  # NaN o Infinity, o más de 10 decimales
        raise ErrorFormulario(f"{nombre} debe ser un número con hasta 10 decimales.", campo)
    return valor


def _catalogo(enum: type[E], codigo: str, permitidos: tuple[E, ...], campo: str, nombre: str) -> E:
    try:
        valor = enum(codigo)
    except ValueError:
        valor = None
    if valor is None or valor not in permitidos:
        raise ErrorFormulario(f"{nombre}: el código '{codigo}' no está entre las opciones del formulario.", campo)
    return valor
