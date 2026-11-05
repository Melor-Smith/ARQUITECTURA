# Evidencia: SUNAT aceptó los comprobantes del sistema

El 05/11/2026 los siete comprobantes de ejemplo del caso se enviaron al **servicio beta de SUNAT** (`https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService`). Se usó la API del propio sistema con el adaptador real `ClienteSunatSoap` ([ADR 0012](../../specs/adr/0012-envio-real-a-sunat-y-validacion-contra-el-servicio-beta.md)). SUNAT respondió con un CDR **código 0 (aceptado)** para cada uno:

| Comprobante | Ejemplo | Qué ejercita | CDR |
|---|---|---|:-:|
| 20556677884-01-F001-1 | [`factura.json`](../../specs/ejemplos/factura.json) | Factura al contado, gravada | **0** |
| 20556677884-01-FA01-1 | [`factura-isc-icbper.json`](../../specs/ejemplos/factura-isc-icbper.json) | ISC en los sistemas 01, 02 y 03, e ICBPER | **0** |
| 20556677884-01-F001-2 | [`factura-credito.json`](../../specs/ejemplos/factura-credito.json) | Venta al crédito con cuotas | **0** |
| 20556677884-01-F001-3 | [`factura-de-vale-legado.json`](../../specs/ejemplos/factura-de-vale-legado.json) | Vale del sistema antiguo como documento relacionado (catálogo 12) | **0** |
| 20556677884-03-B001-1 | [`boleta.json`](../../specs/ejemplos/boleta.json) | Boleta a cliente con DNI | **0** |
| 20556677884-07-FC01-1 | [`nota-credito.json`](../../specs/ejemplos/nota-credito.json) | Nota de crédito (catálogo 09) | **0** |
| 20556677884-08-FD01-1 | [`nota-debito.json`](../../specs/ejemplos/nota-debito.json) | Nota de débito (catálogo 10) | **0** |

## Contenido

| Ruta | Qué es |
|---|---|
| [`enviados/`](enviados) | Cada XML firmado, exactamente como viajó a SUNAT |
| [`respuestas/`](respuestas) | Cada respuesta SOAP de SUNAT, con el CDR (`R-….xml`) en Base64 |
| [`resultado.json`](resultado.json) | Resumen: estado y CDR que registró el sistema para cada comprobante |

## Por qué es confiable

- **Se re-verifica en cada CI sin red** (`tests/integration/test_evidencia_sunat.py`):
  - cada respuesta se vuelve a interpretar con el adaptador de producción;
  - cada CDR responde a su comprobante (serie, emisor y receptor);
  - la firma de cada XML enviado es válida;
  - el código actual **regenera los mismos siete XML** que SUNAT aceptó (sin contar firma ni hora). Si un cambio altera el XML, la prueba falla hasta que se vuelva a validar contra SUNAT.
- **Se repite en vivo** cada lunes y a demanda con el workflow [`sunat-beta.yml`](../../.github/workflows/sunat-beta.yml).

## Lo que SUNAT detectó y la OSE simulada no

En el primer envío, SUNAT rechazó FA01-1 por dos reglas que el XSD no expresa: la **3108** (tasa del ISC de monto fijo) y la **3277** (base global del IGV sin ISC). Las dos se corrigieron y quedaron como pruebas de regresión. El detalle está en el [ADR 0012](../../specs/adr/0012-envio-real-a-sunat-y-validacion-contra-el-servicio-beta.md#lo-que-encontró-sunat).

## Repetirlo

```bash
python scripts/validar_en_sunat_beta.py     # requiere internet; no tiene efecto tributario
```

Si SUNAT responde 401 o 503, el comprobante queda `PENDIENTE_ENVIO` (202) y el script lo reenvía por `POST …/envios`, el mismo camino que usaría un operador.

**Beta no es producción.** No valida contra el padrón RUC y acepta certificados autofirmados. En producción se usa el mismo adaptador con `ABC_SUNAT_ENDPOINT=produccion`, certificado digital y usuario SOL secundario reales.
