"""PLE de extremo a extremo: los datos registrados por la API producen TXT que cumplen el Anexo 2.

Se emiten todos los comprobantes de ejemplo y se migra el lote del sistema antiguo; luego
cada línea de los TXT 14.1 y 12.1 se valida campo por campo, como lo haría el programa PLE.
"""

from __future__ import annotations

from src.domain.ple_estructura import ESTRUCTURA_121, ESTRUCTURA_141, validar_linea
from tests.conftest import ALMACEN, CONSULTA, ejemplo

URL_141 = "/api/v1/libros-electronicos/registro-ventas/202610"
URL_121 = "/api/v1/libros-electronicos/inventario-unidades-fisicas/202610"
COMPROBANTES = ("factura.json", "factura-isc-icbper.json", "factura-credito.json", "factura-de-vale-legado.json",
                "boleta.json", "nota-credito.json", "nota-debito.json")


def _registrar_todo(cliente, emitir, migrar):
    for ficha in ("ficha-legado-salida.json", "ficha-legado-ingreso.json"):
        assert migrar(ejemplo(ficha)).status_code == 201
    r = cliente.post("/api/v1/inventario/migraciones/lotes", json=ejemplo("lote-fichas-legado.json"), headers=ALMACEN)
    assert r.status_code == 201
    for nombre in COMPROBANTES:
        assert emitir(ejemplo(nombre)).status_code in (200, 201), nombre


def _lineas(texto: str) -> list[str]:
    assert texto.endswith("\r\n") and "\n" not in texto.replace("\r\n", "")
    return texto.split("\r\n")[:-1]


def test_registro_de_ventas_141_cumple_el_anexo_2(cliente, emitir, migrar):
    _registrar_todo(cliente, emitir, migrar)
    lineas = _lineas(cliente.get(URL_141, headers=CONSULTA).text)
    assert len(lineas) == len(COMPROBANTES)
    errores = [e for n, ln in enumerate(lineas, 1) for e in validar_linea(ESTRUCTURA_141, ln, n)]
    assert errores == []


def test_inventario_121_cumple_el_anexo_2(cliente, emitir, migrar):
    _registrar_todo(cliente, emitir, migrar)
    lineas = _lineas(cliente.get(URL_121, headers=CONSULTA).text)
    assert lineas
    errores = [e for n, ln in enumerate(lineas, 1) for e in validar_linea(ESTRUCTURA_121, ln, n)]
    assert errores == []
    salidas = [ln.split("|")[17] for ln in lineas if ln.split("|")[17] != "0.00"]
    assert salidas and all(s.startswith("-") for s in salidas)


def test_credito_a_mas_de_un_mes_deja_vacio_el_campo_5(cliente, emitir):
    emitir(ejemplo("factura-credito.json"))  # última cuota: 15/02/2027, emitida en octubre de 2026
    [linea] = _lineas(cliente.get(URL_141, headers=CONSULTA).text)
    assert linea.split("|")[4] == ""


def test_credito_que_vence_el_mes_siguiente_informa_el_campo_5(cliente, emitir):
    payload = ejemplo("factura-credito.json")
    payload["forma_pago"]["cuotas"] = [{"monto": "247.80", "fecha_vencimiento": "2026-11-20"}]
    assert emitir(payload).status_code == 201
    [linea] = _lineas(cliente.get(URL_141, headers=CONSULTA).text)
    assert linea.split("|")[4] == "20/11/2026"


def test_boleta_a_cliente_no_identificado_deja_vacios_los_campos_10_y_11(cliente, emitir):
    payload = ejemplo("boleta.json")
    payload["cliente"] = {"tipo_documento": "0", "numero_documento": "0", "nombre": "CLIENTES VARIOS"}
    assert emitir(payload).status_code == 201, emitir(payload).json()
    [linea] = _lineas(cliente.get(URL_141, headers=CONSULTA).text)
    v = linea.split("|")
    assert (v[9], v[10], v[11]) == ("", "", "CLIENTES VARIOS")
    assert validar_linea(ESTRUCTURA_141, linea) == []


def test_vista_json_usa_el_mismo_formato_que_el_txt(cliente, migrar):
    migrar(ejemplo("ficha-legado-salida.json"))
    filas = cliente.get(f"{URL_121}?formato=json", headers=CONSULTA).json()["filas"]
    salida = next(f for f in filas if f["salida"] != "0.00")
    assert salida["salida"].startswith("-") and "saldo_final" in salida
    assert salida["catalogo_internacional"] == ""
