"""Conversión entre los agregados del dominio y JSON, guiada por sus anotaciones de tipo.

El adaptador SQL guarda cada agregado como un documento JSON junto a columnas indexadas.
Este codec evita dos atajos que un adaptador de persistencia no debería tomar:

* **pickle**: ejecutaría código arbitrario si alguien altera la base de datos, y ata los
  datos guardados a los detalles internos de las clases;
* **un mapeo escrito a mano por clase**: duplicaría el modelo y divergiría con el tiempo.

Reglas: ``Decimal`` → texto (sin pérdida), fechas → ISO 8601, ``bytes`` → base64, ``Enum``
→ su código oficial. Una unión con más de un tipo posible se guarda **etiquetada** con el
nombre de la clase, porque hay códigos repetidos entre catálogos (el Catálogo 09 y el 10
comparten el código "01"). Al reconstruir, los ``__post_init__`` del dominio vuelven a
validar los datos: un registro alterado no produce un agregado inválido en silencio.
"""

from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import json
import types
import typing
from decimal import Decimal
from enum import Enum
from functools import cache
from typing import Any, TypeVar, Union, get_args, get_origin

T = TypeVar("T")
_ETIQUETA = "__tipo__"


def a_json(objeto: object) -> str:
    return json.dumps(_codificar(objeto), ensure_ascii=False, separators=(",", ":"))


def desde_json(clase: type[T], texto: str) -> T:
    resultado: T = _decodificar(clase, json.loads(texto))
    return resultado


# --- codificación ---------------------------------------------------------------------
def _codificar(valor: Any) -> Any:
    if isinstance(valor, Enum):  # antes que str: los catálogos son enums de texto
        return valor.value
    if valor is None or isinstance(valor, bool | int | str):
        return valor
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, dt.datetime | dt.date | dt.time):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return base64.b64encode(valor).decode("ascii")
    if dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        anotaciones = _tipos(type(valor))
        return {f.name: _codificar_campo(anotaciones[f.name], getattr(valor, f.name))
                for f in dataclasses.fields(valor)}
    if isinstance(valor, list | tuple):
        return [_codificar(v) for v in valor]
    if isinstance(valor, dict):
        return {str(k): _codificar(v) for k, v in valor.items()}
    raise TypeError(f"No se sabe guardar un valor de tipo {type(valor).__name__}")


def _codificar_campo(tipo: Any, valor: Any) -> Any:
    """Un campo cuyo tipo admite varias clases se etiqueta para poder reconstruirlo."""
    if valor is not None and _es_union(tipo) and len([o for o in get_args(tipo) if o is not type(None)]) > 1:
        return {_ETIQUETA: type(valor).__name__, "valor": _codificar(valor)}
    return _codificar(valor)


# --- decodificación -------------------------------------------------------------------
@cache
def _tipos(clase: type) -> dict[str, Any]:
    return typing.get_type_hints(clase)


def _es_union(tipo: Any) -> bool:
    return get_origin(tipo) in (Union, types.UnionType)


def _decodificar(tipo: Any, dato: Any) -> Any:
    if _es_union(tipo):
        opciones = get_args(tipo)
        if dato is None:
            return None
        concretas = [o for o in opciones if o is not type(None)]
        if len(concretas) == 1:
            return _decodificar(concretas[0], dato)
        elegida = next(o for o in concretas if getattr(o, "__name__", "") == dato[_ETIQUETA])
        return _decodificar(elegida, dato["valor"])
    origen = get_origin(tipo)
    if origen is tuple:
        argumentos = get_args(tipo)
        if len(argumentos) == 2 and argumentos[1] is Ellipsis:
            return tuple(_decodificar(argumentos[0], v) for v in dato)
        return tuple(_decodificar(a, v) for a, v in zip(argumentos, dato, strict=True))
    if origen is list:
        (argumento,) = get_args(tipo)
        return [_decodificar(argumento, v) for v in dato]
    if origen is dict:
        clave, valor = get_args(tipo)
        return {_decodificar(clave, k): _decodificar(valor, v) for k, v in dato.items()}
    if tipo is Any or dato is None:
        return dato
    if isinstance(tipo, type):
        if issubclass(tipo, Enum):
            return tipo(dato)
        if tipo is Decimal:
            return Decimal(dato)
        if tipo is dt.datetime:
            return dt.datetime.fromisoformat(dato)
        if tipo is dt.date:
            return dt.date.fromisoformat(dato)
        if tipo is dt.time:
            return dt.time.fromisoformat(dato)
        if tipo is bytes:
            return base64.b64decode(dato)
        if dataclasses.is_dataclass(tipo):
            anotaciones = _tipos(tipo)
            campos = {f.name: _decodificar(anotaciones[f.name], dato[f.name])
                      for f in dataclasses.fields(tipo) if f.init and f.name in dato}
            constructor: Any = tipo
            return constructor(**campos)
        if tipo is str:
            return str(dato)
        if tipo is int:
            return int(dato)
        if tipo is bool:
            return bool(dato)
    raise TypeError(f"No se sabe reconstruir el tipo {tipo!r}")

