"""Lectura del contrato escrito a mano y comparación con lo que implementa el código (ADR 0013).

El contrato es ``specs/contracts/openapi.yaml`` más los JSON Schemas 2020-12 de
``specs/contracts/schemas/``. Este módulo:

* resuelve las referencias externas (``schemas/linea.schema.json``) y devuelve el contrato
  **empaquetado**: un solo documento OpenAPI, con la misma forma que el que publica FastAPI;
* compara ese contrato con el OpenAPI del código y lista cada diferencia en lenguaje claro.

Lo usan ``tests/acceptance/test_contrato.py`` (la CI falla si hay diferencias) y
``scripts/exportar_openapi.py`` (las muestra para que el desarrollador corrija el código).
La dirección es siempre la misma: **el contrato manda y el código lo implementa**.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / "specs" / "contracts" / "openapi.yaml"
DIRECTORIO_ESQUEMAS = CONTRATO.parent / "schemas"
PREFIJO_COMPONENTE = "#/components/schemas/"
PLANIFICADO = "planificado"
METODOS = ("get", "put", "post", "delete", "patch")

#: Palabras clave que describen una restricción (las que se comparan con el código).
_RESTRICCIONES = ("pattern", "format", "minLength", "maxLength", "minItems", "maxItems",
                  "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")
#: Metadatos de un JSON Schema suelto que no aportan nada dentro del OpenAPI empaquetado.
_SOLO_DEL_ARCHIVO = ("$schema", "$id", "$defs")

Esquema = dict[str, Any]


class Contrato:
    """El contrato tal como está escrito en ``specs/contracts``."""

    def __init__(self, ruta: Path = CONTRATO) -> None:
        self.ruta = ruta.resolve()
        self._documentos: dict[Path, Any] = {}

    # --- lectura y resolución de $ref -------------------------------------------------
    def documento(self, ruta: Path) -> Any:
        ruta = ruta.resolve()
        if ruta not in self._documentos:
            texto = ruta.read_text(encoding="utf-8")
            self._documentos[ruta] = yaml.safe_load(texto) if ruta.suffix in (".yaml", ".yml") else json.loads(texto)
        return self._documentos[ruta]

    @property
    def openapi(self) -> Esquema:
        documento: Esquema = self.documento(self.ruta)
        return documento

    def resolver(self, ref: str, base: Path) -> tuple[tuple[Path, str], Any]:
        """``'linea.schema.json#/$defs/Isc'`` relativo a ``base`` -> ((archivo, puntero), contenido)."""
        archivo, _, puntero = ref.partition("#")
        ruta = (base.parent / archivo).resolve() if archivo else base.resolve()
        nodo = self.documento(ruta)
        for parte in [p for p in puntero.split("/") if p]:
            nodo = nodo[parte.replace("~1", "/").replace("~0", "~")]
        return (ruta, puntero), nodo

    @cached_property
    def _nombres(self) -> dict[tuple[Path, str], str]:
        """Destino canónico de cada componente -> su nombre en ``components.schemas``."""
        nombres = {}
        for nombre, definicion in self.openapi["components"]["schemas"].items():
            nombres[(self.ruta, f"/components/schemas/{nombre}")] = nombre
            if "$ref" in definicion:
                destino, _ = self.resolver(definicion["$ref"], self.ruta)
                nombres[destino] = nombre
        return nombres

    def esquemas_externos(self) -> dict[str, Path]:
        """Componente -> archivo JSON Schema donde está escrito (solo los que viven en ``schemas/``)."""
        return {nombre: self.resolver(d["$ref"], self.ruta)[0][0]
                for nombre, d in self.openapi["components"]["schemas"].items() if "$ref" in d}

    # --- empaquetado ------------------------------------------------------------------
    def empaquetado(self) -> Esquema:
        """El OpenAPI con cada ``$ref`` externo resuelto.

        Una referencia a algo que es componente queda como ``#/components/schemas/Nombre``;
        el resto se copia en su lugar. Así el resultado tiene la misma forma que el OpenAPI
        que genera FastAPI y ambos se pueden comparar campo por campo.
        """
        resultado = copy.deepcopy({k: v for k, v in self.openapi.items() if k != "components"})
        resultado = self._expandir(resultado, self.ruta, None)
        componentes = copy.deepcopy(self.openapi["components"])
        componentes["schemas"] = {nombre: self._expandir(definicion, self.ruta, nombre)
                                  for nombre, definicion in componentes["schemas"].items()}
        resultado["components"] = componentes
        return resultado

    def _expandir(self, nodo: Any, base: Path, componente: str | None) -> Any:
        if isinstance(nodo, list):
            return [self._expandir(x, base, None) for x in nodo]
        if not isinstance(nodo, dict):
            return nodo
        if "$ref" not in nodo:
            return {k: self._expandir(v, base, None) for k, v in nodo.items() if k not in _SOLO_DEL_ARCHIVO}
        destino, contenido = self.resolver(nodo["$ref"], base)
        hermanos = {k: self._expandir(v, base, None) for k, v in nodo.items() if k != "$ref"}
        nombre = self._nombres.get(destino)
        if nombre is not None and nombre != componente:
            return {"$ref": PREFIJO_COMPONENTE + nombre, **hermanos}
        return {**self._expandir(contenido, destino[0], None), **hermanos}


# --- comparación contrato <-> código ---------------------------------------------------
def _ramas(esquema: Esquema) -> tuple[list[Esquema], bool]:
    """Ramas no nulas de un esquema y si admite null (``anyOf`` o ``type: [x, "null"]``)."""
    ramas = esquema.get("anyOf") or esquema.get("oneOf") or [esquema]
    no_nulas = [r for r in ramas if r.get("type") != "null"]
    nulo = len(no_nulas) != len(ramas) or "null" in (esquema.get("type") or [])
    return no_nulas, nulo


def _tipos(rama: Esquema) -> set[str]:
    if "$ref" in rama:
        return {rama["$ref"].removeprefix(PREFIJO_COMPONENTE)}
    tipo = rama.get("type")
    if tipo is None:
        return set()
    return {t for t in ([tipo] if isinstance(tipo, str) else tipo) if t != "null"}


def _numero(valor: Any) -> Any:
    return float(valor) if isinstance(valor, int | float) and not isinstance(valor, bool) else valor


def facetas(esquema: Esquema) -> dict[str, Any]:
    """Lo que un esquema exige, sin importar cómo esté escrito (anyOf, lista de tipos, const...)."""
    ramas, nulo = _ramas(esquema)
    tipos: set[str] = set().union(*(_tipos(r) for r in ramas)) if ramas else set()
    resultado: dict[str, Any] = {"tipos": sorted(tipos), "nulo": nulo}
    decimal = {"number", "string"} <= tipos
    for rama in ramas:
        valores = rama.get("enum", [rama["const"]] if "const" in rama else None)
        if valores is not None:
            resultado["valores"] = sorted(valores)
        for clave in _RESTRICCIONES:
            # La cadena de un decimal puede tener un patrón más estricto en el contrato
            # (hasta N decimales); Pydantic lo controla con decimal_places, no con pattern.
            if clave in rama and not (decimal and clave == "pattern"):
                resultado[clave] = _numero(rama[clave])
        if "items" in rama:
            resultado["items"] = facetas(rama["items"])
    for fuente in (esquema, *ramas):
        if fuente.get("default") is not None:
            resultado["default"] = fuente["default"]
    return resultado


def _diferencias_objeto(nombre: str, contrato: Esquema, codigo: Esquema) -> Iterator[str]:
    props_c, props_i = contrato.get("properties", {}), codigo.get("properties", {})
    if set(props_c) != set(props_i):
        if faltan := sorted(set(props_c) - set(props_i)):
            yield f"{nombre}: el código no implementa {faltan}"
        if sobran := sorted(set(props_i) - set(props_c)):
            yield f"{nombre}: el código tiene campos que el contrato no declara {sobran}"
    if set(contrato.get("required", [])) != set(codigo.get("required", [])):
        yield (f"{nombre}: obligatorios distintos; contrato {sorted(contrato.get('required', []))}, "
               f"código {sorted(codigo.get('required', []))}")
    if contrato.get("additionalProperties") != codigo.get("additionalProperties"):
        yield (f"{nombre}: additionalProperties; contrato {contrato.get('additionalProperties')}, "
               f"código {codigo.get('additionalProperties')}")
    for campo in sorted(set(props_c) & set(props_i)):
        f_c, f_i = facetas(props_c[campo]), facetas(props_i[campo])
        for clave in sorted(set(f_c) | set(f_i)):
            if f_c.get(clave) != f_i.get(clave):
                yield f"{nombre}.{campo}: {clave}; contrato {f_c.get(clave)!r}, código {f_i.get(clave)!r}"


def _es_planificado(nodo: Esquema) -> bool:
    return nodo.get("x-estado") == PLANIFICADO


def _diferencias_esquemas(contrato: Esquema, codigo: Esquema) -> Iterator[str]:
    esquemas_c, esquemas_i = contrato["components"]["schemas"], codigo["components"]["schemas"]
    for nombre in sorted(set(esquemas_i) - set(esquemas_c)):
        yield f"components.schemas.{nombre}: el código lo publica y el contrato no lo declara"
    for nombre in sorted(set(esquemas_c) - set(esquemas_i)):
        if not _es_planificado(esquemas_c[nombre]):
            yield f"components.schemas.{nombre}: el contrato lo declara y el código no lo implementa"
    for nombre in sorted(set(esquemas_c) & set(esquemas_i)):
        c, i = esquemas_c[nombre], esquemas_i[nombre]
        if "properties" in c or "properties" in i:
            yield from _diferencias_objeto(nombre, c, i)
        elif facetas(c) != facetas(i):
            yield f"{nombre}: contrato {facetas(c)}, código {facetas(i)}"
    if contrato["components"].get("securitySchemes") != codigo["components"].get("securitySchemes"):
        yield "components.securitySchemes: el esquema de seguridad difiere"


def _firma_operacion(operacion: Esquema) -> dict[str, Any]:
    """Lo verificable de una operación: parámetros, cuerpo, respuestas y sus tipos de contenido."""
    cuerpo = operacion.get("requestBody", {}).get("content", {})
    return {
        "parametros": sorted((p["name"], p["in"], bool(p.get("required"))) for p in operacion.get("parameters", [])),
        "cuerpo": {tipo: facetas(c.get("schema", {})) for tipo, c in cuerpo.items()},
        "cuerpo_obligatorio": bool(operacion.get("requestBody", {}).get("required")),
        "respuestas": {codigo: {tipo: facetas(c.get("schema", {})) for tipo, c in r.get("content", {}).items()}
                       for codigo, r in operacion.get("responses", {}).items()},
        "seguridad": operacion.get("security", []),
    }


def _operaciones(documento: Esquema) -> dict[tuple[str, str], Esquema]:
    return {(ruta, metodo): op for ruta, ops in documento.get("paths", {}).items()
            for metodo, op in ops.items() if metodo in METODOS}


def _diferencias_rutas(contrato: Esquema, codigo: Esquema) -> Iterator[str]:
    ops_c, ops_i = _operaciones(contrato), _operaciones(codigo)
    for ruta, metodo in sorted(set(ops_i) - set(ops_c)):
        yield f"{metodo.upper()} {ruta}: el código la expone y el contrato no la declara"
    for ruta, metodo in sorted(set(ops_c) - set(ops_i)):
        if not _es_planificado(ops_c[(ruta, metodo)]):
            yield f"{metodo.upper()} {ruta}: el contrato la declara y el código no la implementa"
    for clave in sorted(set(ops_c) & set(ops_i)):
        ruta, metodo = clave
        if _es_planificado(ops_c[clave]):
            yield f"{metodo.upper()} {ruta}: ya está implementada; quite x-estado: planificado del contrato"
        f_c, f_i = _firma_operacion(ops_c[clave]), _firma_operacion(ops_i[clave])
        for aspecto in f_c:
            if f_c[aspecto] != f_i[aspecto]:
                yield f"{metodo.upper()} {ruta}: {aspecto}; contrato {f_c[aspecto]}, código {f_i[aspecto]}"


def diferencias(contrato: Esquema, codigo: Esquema) -> list[str]:
    """Cada diferencia entre el contrato empaquetado y el OpenAPI del código. Vacía = el código cumple."""
    return [*_diferencias_rutas(contrato, codigo), *_diferencias_esquemas(contrato, codigo)]
