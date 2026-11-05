"""El correlativo se asigna de forma atómica: nunca se repite, aunque haya emisiones simultáneas."""

from concurrent.futures import ThreadPoolExecutor

from src.adapters.outbound.persistencia.memoria import SecuenciaCorrelativosEnMemoria
from src.domain.catalogos import TipoComprobante
from src.domain.valores import Ruc, Serie
from tests.conftest import ejemplo


def test_secuencia_atomica_bajo_concurrencia():
    secuencia = SecuenciaCorrelativosEnMemoria()
    ruc, serie = Ruc("20556677884"), Serie("F001")
    with ThreadPoolExecutor(max_workers=16) as pool:
        numeros = list(pool.map(lambda _: secuencia.siguiente(ruc, TipoComprobante.FACTURA, serie).valor, range(200)))
    assert sorted(numeros) == list(range(1, 201))


def test_las_series_son_independientes_por_tipo():
    secuencia = SecuenciaCorrelativosEnMemoria()
    ruc, serie = Ruc("20556677884"), Serie("F001")
    assert secuencia.siguiente(ruc, TipoComprobante.FACTURA, serie).valor == 1
    assert secuencia.siguiente(ruc, TipoComprobante.NOTA_CREDITO, serie).valor == 1


def test_emisiones_http_simultaneas_no_repiten_ni_sobrescriben(emitir, cliente):
    payload = ejemplo("boleta.json")
    with ThreadPoolExecutor(max_workers=8) as pool:
        respuestas = list(pool.map(lambda _: emitir(payload), range(20)))
    assert {r.status_code for r in respuestas} == {201}
    numeros = {r.json()["serie_numero"] for r in respuestas}
    assert numeros == {f"B001-{n}" for n in range(1, 21)}
