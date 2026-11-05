# ADR 0009: Migración por lotes, clasificación de documentos y observaciones

- **Estado:** aceptado (2026-11-05).
- **Complementa:** ADR 0007.

## Contexto

La primera versión migraba una ficha por vez y trataba todo `nro_documento` como documento interno (tabla 10, tipo 00). En la práctica, el sistema antiguo tiene varios problemas:

- **`nro_documento` no siempre es un vale.** Ahí también se anotaban facturas físicas de proveedores (`FACT 001-4587`), boletas (`B001-0000231`), guías de remisión (`GUIA 0002-781`) y "s/n". Tratarlo todo como tipo 00 deforma el 12.1 y, peor aún, deja "pendientes de facturar" salidas que **ya se facturaron** en papel.
- **Las fechas tienen varios formatos** (`15/10/2026`, `16-10-2026`, `19/10/26`), y algunas son imposibles (`31/09/2026`).
- **El archivo viene desordenado**, pero el Kardex exige orden cronológico.
- **Una ficha mala no debe detener la migración** de miles de fichas buenas.

## Decisión

1. **`clasificar_documento_legado`** (dominio) aplica reglas en orden: sin documento → documento interno → comprobante electrónico → factura física → boleta física → guía de remisión → no reconocido. Cada movimiento registra qué regla se aplicó (`regla_documento`).
2. **Una salida respaldada por factura o boleta** del sistema antiguo queda `FACTURADA_EN_SISTEMA_ANTIGUO` y no se vuelve a facturar. Una respaldada por guía o vale queda `PENDIENTE_FACTURACION`.
3. **Las observaciones no bloquean.** "Sin documento" y "no reconocido" migran la ficha, pero anotan una observación para revisión humana. Nada se inventa en silencio.
4. **`parsear_fecha_legado`** acepta los formatos del sistema antiguo; una fecha imposible es `ERR-LEGADO-FECHA` (422).
5. **Los lotes** (`POST /inventario/migraciones/lotes`):
   - ordenan por fecha;
   - aplican las mismas reglas que la migración individual;
   - marcan cada ficha como `MIGRADA`, `OBSERVADA` (con su código de error) o `DUPLICADA`;
   - concilian por producto: saldo inicial + entradas − salidas = saldo final del Kardex.
6. **Detección de duplicados** por `nro_documento`. Las fichas "s/n" se identifican por un resumen de su contenido, así que reprocesar un archivo es idempotente.

## Consecuencias

- El corte de migración se puede ensayar varias veces: cada lote queda auditado (`GET …/lotes/{id}`).
- La migración individual mantiene su semántica estricta (422 inmediato), útil para la captura en almacén. El lote es el modo para datos históricos.
- **Orden del corte.** Como el Kardex exige orden cronológico, el lote histórico debe migrarse **antes** de empezar a vender con el sistema nuevo. Si un producto ya tiene ventas posteriores, sus fichas antiguas quedan OBSERVADAS con `ERR-KARDEX-FECHA` en lugar de alterar saldos ya informados.
- **Fuera de alcance:**
  - comparación aproximada de glosas (hoy la homologación es exacta, sin tildes ni mayúsculas);
  - aprobación formal del corte por roles.
