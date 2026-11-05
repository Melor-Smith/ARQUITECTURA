"""Persistencia SQLite: lo que solo una base de datos real puede demostrar.

* los datos sobreviven a un reinicio del servidor y el correlativo continúa;
* una emisión que falla no consume correlativo ni deja datos a medias (rollback);
* en un lote, la ficha que falla se deshace sola (SAVEPOINT) y las buenas se conservan;
* la base de datos impide duplicados aunque el código fallara;
* el correlativo es único bajo concurrencia.
"""

from __future__ import annotations

import threading
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.adapters.inbound.http.app import crear_app
from src.adapters.outbound.persistencia.sqlite import BaseDatosSqlite, RepositorioComprobantesSqlite
from src.application.errores import Conflicto
from src.bootstrap import construir_contenedor
from src.config import Configuracion
from tests.conftest import ALMACEN, CONSULTA, FACTURADOR, URL_COMPROBANTES, ejemplo


@pytest.fixture
def ruta(tmp_path):
    return tmp_path / "abc.db"


_ABIERTOS: list = []


@pytest.fixture(autouse=True)
def _cerrar_al_terminar():
    yield
    while _ABIERTOS:
        _ABIERTOS.pop().cerrar()


def _servidor(ruta, reloj):
    """Simula un proceso del servidor: cada llamada abre su propia conexión a la misma base."""
    contenedor = construir_contenedor(Configuracion(base_datos=ruta), reloj=reloj)
    _ABIERTOS.append(contenedor)
    return TestClient(crear_app(contenedor))


def _bd(ruta) -> BaseDatosSqlite:
    bd = BaseDatosSqlite(ruta)
    _ABIERTOS.append(bd)
    return bd


def test_los_datos_sobreviven_a_un_reinicio_y_el_correlativo_continua(ruta, reloj):
    primero = _servidor(ruta, reloj)
    assert primero.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=FACTURADOR).json()[
        "serie_numero"] == "F001-1"

    reiniciado = _servidor(ruta, reloj)  # nuevo proceso, misma base de datos
    consulta = reiniciado.get(f"{URL_COMPROBANTES}/01/F001-1", headers=CONSULTA)
    assert (consulta.status_code, consulta.json()["estado"]) == (200, "ACEPTADO")
    assert reiniciado.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=FACTURADOR).json()[
        "serie_numero"] == "F001-2"
    xml = reiniciado.get(f"{URL_COMPROBANTES}/01/F001-1/xml", headers=CONSULTA)
    assert xml.status_code == 200 and b"SignatureValue" in xml.content  # la firma se guardó intacta


def test_reiniciar_no_duplica_el_inventario_inicial(ruta, reloj):
    _servidor(ruta, reloj)
    reiniciado = _servidor(ruta, reloj)
    kardex = reiniciado.get("/api/v1/inventario/kardex/AB-ARR-001", headers=CONSULTA).json()
    assert len(kardex["movimientos"]) == 1 and kardex["saldo_final"] == "2000"


def test_una_emision_fallida_no_consume_correlativo_ni_deja_rastros(ruta, reloj):
    cliente = _servidor(ruta, reloj)
    sin_stock = ejemplo("factura.json")
    sin_stock["lineas"][0]["cantidad"] = "999999"  # más que el saldo del Kardex: 422
    assert cliente.post(URL_COMPROBANTES, json=sin_stock, headers=FACTURADOR).status_code == 422

    assert cliente.post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=FACTURADOR).json()[
        "serie_numero"] == "F001-1"  # el 1 no se perdió
    assert _bd(ruta).uno("SELECT COUNT(*) FROM comprobante") == (1,)


def test_en_un_lote_la_ficha_que_falla_se_deshace_sola(ruta, reloj):
    cliente = _servidor(ruta, reloj)
    lote = cliente.post("/api/v1/inventario/migraciones/lotes", json=ejemplo("lote-fichas-legado.json"),
                        headers=ALMACEN).json()
    observadas = [r for r in lote["resultados"] if r["estado"] == "OBSERVADA"]
    migradas = [r for r in lote["resultados"] if r["estado"] == "MIGRADA"]
    assert observadas and migradas
    assert lote["resumen"]["cuadra"] is True  # nada a medias de las fichas observadas

    reiniciado = _servidor(ruta, reloj)
    guardado = reiniciado.get(f"/api/v1/inventario/migraciones/lotes/{lote['id_lote']}", headers=CONSULTA).json()
    assert guardado["resumen"] == lote["resumen"]


def test_la_base_de_datos_impide_comprobantes_duplicados(ruta, reloj):
    _servidor(ruta, reloj).post(URL_COMPROBANTES, json=ejemplo("factura.json"), headers=FACTURADOR)
    repositorio = RepositorioComprobantesSqlite(_bd(ruta))
    [factura] = list(repositorio.listar())
    with pytest.raises(Conflicto) as error:
        repositorio.agregar(factura)
    assert error.value.codigo == "ERR-COMPROBANTE-DUPLICADO"


def test_correlativos_unicos_bajo_concurrencia(ruta, reloj):
    cliente = _servidor(ruta, reloj)
    pequena = ejemplo("factura.json")
    pequena["lineas"][0]["cantidad"] = "1"
    numeros: list[str] = []
    errores: list[int] = []

    def emitir() -> None:
        r = cliente.post(URL_COMPROBANTES, json=pequena, headers=FACTURADOR)
        (numeros.append(r.json()["serie_numero"]) if r.status_code == 201 else errores.append(r.status_code))

    hilos = [threading.Thread(target=emitir) for _ in range(12)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert errores == []
    assert sorted(numeros, key=lambda n: int(n.split("-")[1])) == [f"F001-{i}" for i in range(1, 13)]


def test_rollback_anidado_conserva_lo_externo(ruta):
    bd = _bd(ruta)
    with bd.transaccion():
        bd.ejecutar("INSERT INTO lote VALUES ('externo', '{}')")
        with pytest.raises(RuntimeError), bd.transaccion():
            bd.ejecutar("INSERT INTO lote VALUES ('interno', '{}')")
            raise RuntimeError("falla una ficha")
    assert [f[0] for f in bd.todos("SELECT id FROM lote")] == ["externo"]


def test_los_importes_se_guardan_sin_perder_precision(ruta, reloj):
    cliente = _servidor(ruta, reloj)
    cliente.post(URL_COMPROBANTES, json=ejemplo("factura-isc-icbper.json"), headers=FACTURADOR)
    total_api = cliente.get(f"{URL_COMPROBANTES}/01/FA01-1", headers=CONSULTA).json()["totales"]["importe_total"]
    reiniciado = _servidor(ruta, reloj)
    total_bd = reiniciado.get(f"{URL_COMPROBANTES}/01/FA01-1", headers=CONSULTA).json()["totales"]["importe_total"]
    assert Decimal(str(total_bd)) == Decimal(str(total_api)) == Decimal("532.15")
