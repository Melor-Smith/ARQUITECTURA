"""El contrato y la implementación no pueden divergir.

1. ``specs/contracts/openapi.yaml`` debe ser idéntico al OpenAPI que genera el código.
   Si se cambia un DTO, hay que regenerarlo: ``python scripts/exportar_openapi.py``.
2. Todo ejemplo de ``specs/ejemplos`` debe ser aceptado por la API.
3. Todos los errores se documentan como ``application/problem+json``.
"""

import json

import pytest
import yaml

from tests.conftest import ALMACEN, EJEMPLOS, FACTURADOR, RAIZ, URL_COMPROBANTES, URL_MIGRACIONES, ejemplo

CONTRATO = RAIZ / "specs" / "contracts" / "openapi.yaml"


def test_el_openapi_versionado_coincide_con_el_generado_por_el_codigo(cliente):
    versionado = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    generado = cliente.app.openapi()
    assert versionado == generado, "El contrato diverge del código: ejecute python scripts/exportar_openapi.py"


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


CONTRAEJEMPLOS = yaml.safe_load((EJEMPLOS / "invalidos" / "esperados.yaml").read_text(encoding="utf-8"))


def test_todos_los_contraejemplos_tienen_expectativa():
    archivos = {p.stem for p in (EJEMPLOS / "invalidos").glob("*.json")}
    assert archivos == set(CONTRAEJEMPLOS)


@pytest.mark.parametrize("nombre", sorted(CONTRAEJEMPLOS))
def test_cada_contraejemplo_se_rechaza_como_se_espera(nombre, cliente, emitir):
    esperado = CONTRAEJEMPLOS[nombre]
    emitir(ejemplo("factura.json"))  # algunas notas necesitan una factura previa
    cuerpo = json.loads((EJEMPLOS / "invalidos" / f"{nombre}.json").read_text(encoding="utf-8"))
    url = URL_COMPROBANTES if esperado["destino"] == "comprobantes" else URL_MIGRACIONES
    r = cliente.post(url, json=cuerpo, headers=FACTURADOR)
    assert r.headers["content-type"].startswith("application/problem+json")
    assert (r.status_code, r.json()["codigo"]) == (esperado["http"], esperado["codigo"]), r.json()


def test_errores_documentados_como_problem_json(cliente):
    esquema = cliente.app.openapi()
    for ruta, operaciones in esquema["paths"].items():
        for metodo, operacion in operaciones.items():
            for codigo, respuesta in operacion["responses"].items():
                if int(codigo) >= 400:
                    assert list(respuesta["content"]) == ["application/problem+json"], (ruta, metodo, codigo)
    assert "HTTPValidationError" not in esquema["components"]["schemas"]


def test_la_emision_documenta_todos_sus_codigos(cliente):
    respuestas = cliente.app.openapi()["paths"]["/api/v1/comprobantes"]["post"]["responses"]
    assert set(respuestas) == {"200", "201", "202", "400", "401", "403", "409", "422"}
    reenvio = cliente.app.openapi()["paths"]["/api/v1/comprobantes/{tipo_comprobante}/{serie_numero}/envios"]
    assert {"502", "503"} <= set(reenvio["post"]["responses"])
