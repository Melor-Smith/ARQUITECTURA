"""Envía los comprobantes de ejemplo al servicio beta de SUNAT y guarda los CDR como evidencia.

Uso:  python scripts/validar_en_sunat_beta.py   →   docs/evidencia-sunat/

Todo pasa por la API del sistema, igual que en producción: ``POST /api/v1/comprobantes``
con el adaptador ``ClienteSunatSoap`` apuntando a beta (``ABC_SUNAT_ENDPOINT=beta``). Si
SUNAT no responde, el comprobante queda ``PENDIENTE_ENVIO`` (202) y se reenvía con
``POST .../envios``, el mismo camino que usaría un operador.

Requiere red. Beta usa el usuario ``RUC + MODDATOS`` y acepta el certificado autofirmado;
no tiene efecto tributario. El procedimiento y los resultados están en
``docs/evidencia-sunat/README.md``.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fastapi.testclient import TestClient  # noqa: E402

from src.adapters.inbound.http.app import crear_app  # noqa: E402
from src.adapters.outbound.ose.sunat_soap import (  # noqa: E402
    ENDPOINT_BETA,
    ClienteSunatSoap,
    RespuestaHttp,
    transporte_urllib,
)
from src.adapters.outbound.persistencia.semillas import EMISOR_ABC  # noqa: E402
from src.adapters.outbound.reloj import RelojSistema  # noqa: E402
from src.bootstrap import construir_contenedor  # noqa: E402
from src.config import Configuracion  # noqa: E402

EJEMPLOS = RAIZ / "specs" / "ejemplos"
DESTINO = RAIZ / "docs" / "evidencia-sunat"
CABECERAS = {"Authorization": "Bearer dev-facturador"}
FICHAS = ("ficha-legado-salida.json", "ficha-legado-ingreso.json")
COMPROBANTES = ("factura.json", "factura-isc-icbper.json", "factura-credito.json", "factura-de-vale-legado.json",
                "boleta.json", "nota-credito.json", "nota-debito.json")
REINTENTOS, PAUSA_SEGUNDOS = 5, 4  # beta responde 401 desde su nginx ante ráfagas de envíos


class TransporteConEvidencia:
    """Transporte real que, además, guarda la respuesta cruda de SUNAT por archivo enviado."""

    def __init__(self) -> None:
        self.respuestas: dict[str, bytes] = {}

    def __call__(self, url: str, cuerpo: bytes, cabeceras: dict[str, str], timeout: float) -> RespuestaHttp:
        time.sleep(PAUSA_SEGUNDOS)
        respuesta = transporte_urllib(url, cuerpo, cabeceras, timeout)
        nombre = re.search(rb"<fileName>(.+?)\.zip</fileName>", cuerpo).group(1).decode()  # type: ignore[union-attr]
        self.respuestas[nombre] = respuesta.cuerpo
        return respuesta


def _cargar(nombre: str) -> dict:
    return json.loads((EJEMPLOS / nombre).read_text(encoding="utf-8"))


def validar() -> tuple[list[dict], dict[str, bytes], dict[str, bytes]]:
    """Devuelve (resultados, XML firmados enviados, respuestas SOAP de SUNAT)."""
    transporte = TransporteConEvidencia()
    reloj = RelojSistema()
    ose = ClienteSunatSoap(ruc=str(EMISOR_ABC.ruc), reloj=reloj, endpoint=ENDPOINT_BETA, transporte=transporte)
    contenedor = construir_contenedor(Configuracion(), reloj=reloj, ose=ose)
    cliente = TestClient(crear_app(contenedor))

    for ficha in FICHAS:
        cliente.post("/api/v1/inventario/migraciones", json=_cargar(ficha), headers=CABECERAS).raise_for_status()
    resultados, enviados = [], {}
    for ejemplo in COMPROBANTES:
        r = cliente.post("/api/v1/comprobantes", json=_cargar(ejemplo), headers=CABECERAS)
        cuerpo, intentos = r.json(), 1
        url = f"/api/v1/comprobantes/{cuerpo['tipo_comprobante']['codigo']}/{cuerpo['serie_numero']}"
        while cuerpo["estado"] == "PENDIENTE_ENVIO" and intentos < REINTENTOS:
            intentos += 1
            cuerpo = cliente.post(f"{url}/envios", headers=CABECERAS).json()
        nombre = f"{contenedor.emisor.ruc}-{cuerpo['tipo_comprobante']['codigo']}-{cuerpo['serie_numero']}"
        enviados[nombre] = cliente.get(f"{url}/xml", headers=CABECERAS).content
        resultados.append({"ejemplo": ejemplo, "comprobante": nombre, "estado": cuerpo["estado"],
                           "cdr": cuerpo["cdr"], "intentos": intentos})
    contenedor.cerrar()
    return resultados, enviados, transporte.respuestas


def main() -> int:
    resultados, enviados, respuestas = validar()
    for carpeta in ("enviados", "respuestas"):
        (DESTINO / carpeta).mkdir(parents=True, exist_ok=True)
    for nombre, xml in enviados.items():
        (DESTINO / "enviados" / f"{nombre}.xml").write_bytes(xml)
    for nombre, cuerpo in respuestas.items():
        (DESTINO / "respuestas" / f"{nombre}.soap.xml").write_bytes(cuerpo)
    (DESTINO / "resultado.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    for r in resultados:
        cdr = r["cdr"] or {"codigo": "-", "descripcion": "sin CDR"}
        print(f"{r['comprobante']:28} {r['estado']:28} {cdr['codigo']:>4}  {cdr['descripcion']}")
    return 0 if all(r["estado"] == "ACEPTADO" for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
