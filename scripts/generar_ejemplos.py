"""Genera en docs/ejemplos/ salidas REALES del sistema (no plantillas) para revisión.

Ejecuta el flujo completo contra la API, con un reloj fijo para que sea reproducible:
migración de vales, factura, factura con ISC/ICBPER, factura de un vale, boleta, notas y
libros PLE 14.1 y 12.1. Uso:  python scripts/generar_ejemplos.py

Nota: el certificado de firma es autofirmado y se genera en cada ejecución, así que la
firma (y por tanto el hash CPE) cambia entre ejecuciones; el resto del XML es estable.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fastapi.testclient import TestClient  # noqa: E402
from lxml import etree  # noqa: E402

from src.adapters.inbound.http.app import crear_app  # noqa: E402
from src.adapters.outbound.reloj import RelojFijo  # noqa: E402
from src.bootstrap import construir_contenedor  # noqa: E402
from src.config import Configuracion  # noqa: E402

EJEMPLOS = RAIZ / "specs" / "ejemplos"
DESTINO = RAIZ / "docs" / "ejemplos"
CABECERAS = {"Authorization": "Bearer dev-facturador"}


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    reloj = RelojFijo(dt.datetime(2026, 10, 22, 10, 30))
    cliente = TestClient(crear_app(construir_contenedor(Configuracion(), reloj=reloj)))

    def cargar(nombre: str) -> dict:
        return json.loads((EJEMPLOS / nombre).read_text(encoding="utf-8"))

    for ficha in ("ficha-legado-salida.json", "ficha-legado-ingreso.json"):
        r = cliente.post("/api/v1/inventario/migraciones", json=cargar(ficha), headers=CABECERAS)
        r.raise_for_status()
        (DESTINO / f"respuesta-migracion-{ficha}").write_text(json.dumps(r.json(), indent=2, ensure_ascii=False),
                                                              encoding="utf-8")

    r = cliente.post("/api/v1/inventario/migraciones/lotes", json=cargar("lote-fichas-legado.json"), headers=CABECERAS)
    r.raise_for_status()
    (DESTINO / "respuesta-lote-fichas-legado.json").write_text(json.dumps(r.json(), indent=2, ensure_ascii=False),
                                                              encoding="utf-8")

    for nombre in ("factura.json", "factura-isc-icbper.json", "factura-credito.json", "factura-de-vale-legado.json",
                   "boleta.json", "nota-credito.json", "nota-debito.json"):
        r = cliente.post("/api/v1/comprobantes", json=cargar(nombre), headers=CABECERAS)
        r.raise_for_status()
        cuerpo = r.json()
        base = nombre.removesuffix(".json")
        (DESTINO / f"respuesta-{base}.json").write_text(json.dumps(cuerpo, indent=2, ensure_ascii=False),
                                                        encoding="utf-8")
        xml = cliente.get(cuerpo["enlaces"]["xml"], headers=CABECERAS).content
        legible = etree.tostring(etree.fromstring(xml), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        (DESTINO / f"{base}-{cuerpo['serie_numero']}.xml").write_bytes(legible)

    for ruta, nombre in (("registro-ventas", "ple-14.1"), ("inventario-unidades-fisicas", "ple-12.1")):
        r = cliente.get(f"/api/v1/libros-electronicos/{ruta}/202610", headers=CABECERAS)
        archivo = r.headers["content-disposition"].split('filename="')[1].rstrip('"')
        (DESTINO / f"{nombre}-{archivo}").write_bytes(r.content)

    (DESTINO / "LEEME.md").write_text(
        "# Salidas reales del sistema\n\n"
        "Generadas con `python scripts/generar_ejemplos.py` (reloj fijo: 22/10/2026 10:30, UTC-5).\n\n"
        "* `*.xml`: XML UBL 2.1 firmado (XMLDSig) tal como lo recibe la OSE. Para leerlo mejor se reindentó, "
        "así que la firma de estas copias ya no verifica: el original está en "
        "`GET /api/v1/comprobantes/{tipo}/{serie_numero}/xml`.\n"
        "* `respuesta-*.json`: vista JSON que devuelve la API.\n"
        "* `ple-14.1-*.txt` y `ple-12.1-*.txt`: TXT del PLE con su nombre de archivo oficial.\n\n"
        "El certificado es autofirmado y de desarrollo; el hash CPE cambia entre ejecuciones.\n",
        encoding="utf-8",
    )
    print(f"Ejemplos generados en {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
