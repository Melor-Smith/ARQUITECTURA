"""Adaptador de entrada por línea de comandos (Taller 2: generar el XML sin servidor HTTP).

Uso:
    python -m src.adapters.inbound.cli generar-xml specs/ejemplos/factura.json [más.json ...]
           [--salida carpeta] [--fecha 2026-10-22]

Cada solicitud pasa por el MISMO caso de uso que la API (EmitirComprobante): se valida, se
calcula, se numera, se genera el XML desde las clases del XSD, se valida contra el XSD, se
firma y se envía a la OSE simulada. Los archivos se procesan en orden, así que una nota de
crédito puede referenciar la factura del archivo anterior.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from src.adapters.inbound.traduccion import LECTOR_COMPROBANTE, comando_emision
from src.adapters.outbound.reloj import RelojFijo
from src.application.errores import ErrorAplicacion
from src.bootstrap import construir_contenedor
from src.config import Configuracion
from src.domain.errores import ErrorDominio


def generar_xml(archivos: list[Path], salida: Path, fecha: dt.date | None) -> int:
    reloj = RelojFijo(dt.datetime.combine(fecha, dt.time(10, 0))) if fecha else None
    contenedor = construir_contenedor(Configuracion(), reloj=reloj)
    salida.mkdir(parents=True, exist_ok=True)
    errores = 0
    for archivo in archivos:
        try:
            cuerpo = LECTOR_COMPROBANTE.validate_python(json.loads(archivo.read_text(encoding="utf-8")))
            comprobante = contenedor.emitir_comprobante.ejecutar(comando_emision(cuerpo)).comprobante
        except ValidationError as exc:
            errores += 1
            print(f"✗ {archivo.name}: no cumple el contrato (400)")
            for e in exc.errors():
                print(f"    {'.'.join(str(p) for p in e['loc'])}: {e['msg']}")
            continue
        except (ErrorDominio, ErrorAplicacion) as exc:
            errores += 1
            print(f"✗ {archivo.name}: {exc.codigo} — {exc.mensaje}")
            continue
        destino = salida / f"{comprobante.nombre_archivo}.xml"
        destino.write_bytes(comprobante.xml_firmado or b"")
        t = comprobante.totales
        print(f"✓ {archivo.name} → {destino}  [{comprobante.estado.value}]  total {t.importe_total} "
              f"{comprobante.moneda.value}  hash {comprobante.hash_cpe}")
    return 1 if errores else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa cp1252 por defecto
    parser = argparse.ArgumentParser(prog="abc-cli", description="Herramientas de ABC Software Corp")
    sub = parser.add_subparsers(dest="comando", required=True)
    gen = sub.add_parser("generar-xml", help="Genera, valida y firma el XML UBL 2.1 de una o más solicitudes JSON")
    gen.add_argument("archivos", nargs="+", type=Path)
    gen.add_argument("--salida", type=Path, default=Path("salida-xml"))
    gen.add_argument("--fecha", type=dt.date.fromisoformat, default=None,
                     help="Fecha de emisión fija (AAAA-MM-DD) para resultados reproducibles")
    args = parser.parse_args(argv)
    return generar_xml(args.archivos, args.salida, args.fecha)


if __name__ == "__main__":
    sys.exit(main())
