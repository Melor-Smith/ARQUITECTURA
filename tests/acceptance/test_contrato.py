"""El contrato se escribe primero y el código lo implementa (spec-first, ADR 0013).

La fuente es ``specs/contracts/openapi.yaml`` más los JSON Schemas 2020-12 de
``specs/contracts/schemas/``, escritos a mano. Estas pruebas van en esa dirección:

1. Los JSON Schemas son válidos y cada ejemplo de ``specs/ejemplos`` los cumple.
2. Los contraejemplos que la API rechaza con 400 tampoco cumplen el schema; los que rechaza
   con 422 sí lo cumplen (son reglas de negocio, no de formato). Así 400 y 422 quedan definidos
   por el contrato, no por la implementación.
3. El código implementa exactamente el contrato: mismas rutas, códigos HTTP, campos,
   obligatorios, catálogos, patrones y límites. ``python scripts/exportar_openapi.py`` muestra
   las diferencias si las hay.
4. Todo ejemplo del contrato es aceptado por la API y todo error es ``application/problem+json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from scripts.contrato import DIRECTORIO_ESQUEMAS, Contrato, diferencias
from tests.conftest import ALMACEN, EJEMPLOS, FACTURADOR, URL_COMPROBANTES, URL_MIGRACIONES, ejemplo

CONTRATO = Contrato()
ARCHIVOS_ESQUEMA = sorted(DIRECTORIO_ESQUEMAS.glob("*.schema.json"))
REGISTRO: Registry = Registry().with_resources(
    (esquema["$id"], Resource.from_contents(esquema))
    for esquema in (json.loads(p.read_text(encoding="utf-8")) for p in ARCHIVOS_ESQUEMA)
)
CONTRAEJEMPLOS = yaml.safe_load((EJEMPLOS / "invalidos" / "esperados.yaml").read_text(encoding="utf-8"))

#: Qué schema del contrato valida cada familia de ejemplos.
ESQUEMA_DE_EJEMPLO = {
    "ficha": "ficha-legado.schema.json",
    "lote": "lote-fichas.schema.json",
    "baja": "baja.schema.json",
    "resumen": "resumen-diario.schema.json",
}


def _validador(nombre: str) -> Draft202012Validator:
    esquema = json.loads((DIRECTORIO_ESQUEMAS / nombre).read_text(encoding="utf-8"))
    return Draft202012Validator(esquema, registry=REGISTRO, format_checker=FormatChecker())


def _esquema_para(archivo: Path) -> str:
    return next((esquema for prefijo, esquema in ESQUEMA_DE_EJEMPLO.items() if archivo.stem.startswith(prefijo)),
                "comprobante-emision.schema.json")


def _errores(nombre_esquema: str, archivo: Path) -> list[str]:
    instancia = json.loads(archivo.read_text(encoding="utf-8"))
    validador = _validador(nombre_esquema)
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in validador.iter_errors(instancia)]


# --- 1. Los schemas y los ejemplos --------------------------------------------------------
@pytest.mark.parametrize("archivo", ARCHIVOS_ESQUEMA, ids=lambda p: p.name)
def test_cada_schema_es_json_schema_2020_12_valido(archivo):
    esquema = json.loads(archivo.read_text(encoding="utf-8"))
    assert esquema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert esquema["$id"].endswith("/" + archivo.name)
    Draft202012Validator.check_schema(esquema)


@pytest.mark.parametrize("archivo", ARCHIVOS_ESQUEMA, ids=lambda p: p.name)
def test_cada_propiedad_del_contrato_esta_documentada(archivo):
    """Cada campo lleva su regla SUNAT o de negocio; las de entrada citan además la matriz."""
    sin_descripcion = []

    def recorrer(nodo: object, ruta: str) -> None:
        if isinstance(nodo, dict):
            for nombre, propiedad in nodo.get("properties", {}).items():
                # Un campo que reutiliza una definición ($ref) hereda su descripción.
                destino = CONTRATO.resolver(propiedad["$ref"], archivo)[1] if "$ref" in propiedad else {}
                if "description" not in propiedad and "description" not in destino:
                    sin_descripcion.append(f"{ruta}.{nombre}")
            for clave, valor in nodo.items():
                recorrer(valor, f"{ruta}.{clave}")

    recorrer(json.loads(archivo.read_text(encoding="utf-8")), archivo.stem)
    assert sin_descripcion == []


EJEMPLOS_VALIDOS = sorted([*EJEMPLOS.glob("*.json"), *(EJEMPLOS / "planificados").glob("*.json")])


@pytest.mark.parametrize("archivo", EJEMPLOS_VALIDOS, ids=lambda p: p.stem)
def test_cada_ejemplo_cumple_el_contrato_escrito(archivo):
    assert _errores(_esquema_para(archivo), archivo) == []


def test_todos_los_contraejemplos_tienen_expectativa():
    archivos = {p.stem for p in (EJEMPLOS / "invalidos").glob("*.json")}
    assert archivos == set(CONTRAEJEMPLOS)


@pytest.mark.parametrize("nombre", sorted(CONTRAEJEMPLOS))
def test_el_contrato_separa_400_de_422(nombre):
    """400 = no cumple el schema; 422 = cumple el schema pero viola una regla SUNAT o de negocio."""
    esperado = CONTRAEJEMPLOS[nombre]
    archivo = EJEMPLOS / "invalidos" / f"{nombre}.json"
    esquema = "comprobante-emision.schema.json" if esperado["destino"] == "comprobantes" else "ficha-legado.schema.json"
    errores = _errores(esquema, archivo)
    if esperado["http"] == 400:
        assert errores, f"{nombre} espera 400, pero cumple el schema: el contrato no lo prohíbe"
    else:
        assert errores == [], f"{nombre} espera {esperado['http']}, pero el schema ya lo rechaza"


# --- 2. El código implementa el contrato --------------------------------------------------
def test_el_codigo_implementa_exactamente_el_contrato(cliente):
    generado = cliente.get("/api/v1/openapi.json").json()
    encontradas = diferencias(CONTRATO.empaquetado(), generado)
    assert encontradas == [], "El código no cumple el contrato (detalle: python scripts/exportar_openapi.py):\n" + \
        "\n".join(encontradas)


#: Pares DTO del código <-> JSON Schema del contrato. Los planificados (ADR 0014) aún no tienen DTO.
PARES_DTO_SCHEMA = sorted((componente, archivo) for componente, archivo in CONTRATO.esquemas_externos().items()
                          if CONTRATO.openapi["components"]["schemas"][componente].get("x-estado") != "planificado")


@pytest.mark.parametrize(("componente", "archivo"), PARES_DTO_SCHEMA, ids=[c for c, _ in PARES_DTO_SCHEMA])
def test_cada_dto_tiene_exactamente_los_campos_de_su_schema(componente, archivo, cliente):
    """El contrato manda: el DTO del código no puede tener ni más ni menos campos que el schema."""
    contrato = CONTRATO.empaquetado()["components"]["schemas"][componente]
    generado = cliente.get("/api/v1/openapi.json").json()["components"]["schemas"][componente]
    assert set(generado.get("properties", {})) == set(contrato.get("properties", {}))
    assert set(generado.get("required", [])) == set(contrato.get("required", []))
    assert generado.get("enum") == contrato.get("enum")


def test_el_contrato_no_se_genera_desde_el_codigo():
    texto = (Path(CONTRATO.ruta)).read_text(encoding="utf-8")
    assert "GENERADO" not in texto.upper().split("OPENAPI:")[0]
    assert "SE ESCRIBEN A MANO" in texto


def test_las_operaciones_planificadas_estan_completas():
    """Lo planificado (ADR 0014) también es contrato: esquema de entrada, ejemplos y errores."""
    planificadas = {(ruta, metodo): op for ruta, ops in CONTRATO.openapi["paths"].items()
                    for metodo, op in ops.items() if op.get("x-estado") == "planificado"}
    assert {ruta for ruta, _ in planificadas} == {
        "/api/v1/comprobantes/{tipo_comprobante}/{serie_numero}/bajas", "/api/v1/bajas/{id}",
        "/api/v1/resumenes-diarios", "/api/v1/resumenes-diarios/{id}"}
    for (ruta, metodo), operacion in planificadas.items():
        assert {"401", "403"} <= set(operacion["responses"]), ruta
        if metodo == "post":
            assert operacion["requestBody"]["content"]["application/json"]["examples"], ruta
            assert {"202", "400", "422", "503"} <= set(operacion["responses"]), ruta


# --- 3. La API acepta los ejemplos y rechaza los contraejemplos como dice el contrato ---------
def test_todos_los_ejemplos_del_contrato_son_aceptados(migrar, emitir, cliente):
    # Orden de negocio: primero se migra el vale, luego se factura; las notas modifican F001-1.
    orden = ["ficha-legado-salida.json", "ficha-legado-ingreso.json", "lote-fichas-legado.json", "factura.json",
             "factura-isc-icbper.json", "factura-credito.json", "factura-de-vale-legado.json", "boleta.json",
             "nota-credito.json", "nota-debito.json"]
    assert sorted(orden) == sorted(p.name for p in EJEMPLOS.glob("*.json")), "Hay ejemplos sin probar"
    for nombre in orden:
        if nombre.startswith("lote"):
            r = cliente.post(f"{URL_MIGRACIONES}/lotes", json=ejemplo(nombre), headers=ALMACEN)
        elif nombre.startswith("ficha"):
            r = migrar(ejemplo(nombre))
        else:
            r = emitir(ejemplo(nombre))
        assert r.status_code == 201, (nombre, r.text)


def test_los_ejemplos_incrustados_en_el_contrato_son_los_de_specs_ejemplos():
    archivos = [json.loads(p.read_text(encoding="utf-8")) for p in EJEMPLOS_VALIDOS]
    for ruta, operaciones in CONTRATO.openapi["paths"].items():
        for operacion in operaciones.values():
            cuerpo = operacion.get("requestBody", {}).get("content", {}).get("application/json", {})
            for nombre, ej in cuerpo.get("examples", {}).items():
                assert ej["value"] in archivos, (ruta, nombre)


@pytest.mark.parametrize("nombre", sorted(CONTRAEJEMPLOS))
def test_cada_contraejemplo_se_rechaza_como_se_espera(nombre, cliente, emitir):
    esperado = CONTRAEJEMPLOS[nombre]
    emitir(ejemplo("factura.json"))  # algunas notas necesitan una factura previa
    cuerpo = json.loads((EJEMPLOS / "invalidos" / f"{nombre}.json").read_text(encoding="utf-8"))
    url = URL_COMPROBANTES if esperado["destino"] == "comprobantes" else URL_MIGRACIONES
    r = cliente.post(url, json=cuerpo, headers=FACTURADOR)
    assert r.headers["content-type"].startswith("application/problem+json")
    assert (r.status_code, r.json()["codigo"]) == (esperado["http"], esperado["codigo"]), r.json()


def test_errores_documentados_como_problem_json():
    esquema = CONTRATO.empaquetado()
    for ruta, operaciones in esquema["paths"].items():
        for metodo, operacion in operaciones.items():
            for codigo, respuesta in operacion["responses"].items():
                if int(codigo) >= 400:
                    assert list(respuesta["content"]) == ["application/problem+json"], (ruta, metodo, codigo)
                    assert respuesta["content"]["application/problem+json"]["schema"] == {
                        "$ref": "#/components/schemas/Problema"}, (ruta, metodo, codigo)
    assert "HTTPValidationError" not in esquema["components"]["schemas"]


def test_la_emision_documenta_todos_sus_codigos():
    rutas = CONTRATO.openapi["paths"]
    assert set(rutas["/api/v1/comprobantes"]["post"]["responses"]) == {
        "200", "201", "202", "400", "401", "403", "409", "422"}
    reenvio = rutas["/api/v1/comprobantes/{tipo_comprobante}/{serie_numero}/envios"]
    assert {"502", "503"} <= set(reenvio["post"]["responses"])
