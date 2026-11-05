# Salidas reales del sistema

Generadas con `python scripts/generar_ejemplos.py` (reloj fijo: 22/10/2026 10:30, UTC-5).

* `*.xml`: XML UBL 2.1 firmado (XMLDSig) tal como lo recibe la OSE. Para leerlo mejor se reindentó, así que la firma de estas copias ya no verifica: el original está en `GET /api/v1/comprobantes/{tipo}/{serie_numero}/xml`.
* `respuesta-*.json`: vista JSON que devuelve la API.
* `ple-14.1-*.txt` y `ple-12.1-*.txt`: TXT del PLE con su nombre de archivo oficial.

El certificado es autofirmado y de desarrollo; el hash CPE cambia entre ejecuciones.
