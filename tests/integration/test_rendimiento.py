"""Atributo de calidad AC-02 (rendimiento): latencia de emisión dentro del proceso.

Mide la emisión completa (validar, calcular, numerar, generar XML, validar XSD dos veces, firmar
y obtener CDR de la OSE simulada). El umbral es holgado para que no falle en equipos lentos; el
valor real se imprime con ``pytest -s``.
"""

import statistics
import time

from tests.conftest import ejemplo

UMBRAL_P95_SEGUNDOS = 0.5


def test_p95_de_la_emision_completa(emitir):
    emitir(ejemplo("boleta.json"))  # calienta la caché de los XSD
    duraciones = []
    for _ in range(40):
        inicio = time.perf_counter()
        assert emitir(ejemplo("boleta.json")).status_code == 201
        duraciones.append(time.perf_counter() - inicio)
    p95 = statistics.quantiles(duraciones, n=20)[18]
    print(f"\nEmisión completa: mediana {statistics.median(duraciones) * 1000:.1f} ms, p95 {p95 * 1000:.1f} ms")
    assert p95 < UMBRAL_P95_SEGUNDOS
