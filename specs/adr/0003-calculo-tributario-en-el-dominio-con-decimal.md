# ADR 0003: El dominio calcula los tributos con Decimal

- **Estado:** aceptado.
- **Observación que atiende:** 5.

## Contexto

El cliente enviaba `igv_item`, `isc_item` y los totales, y el servidor los aceptaba sin recalcular: con `importe_total = 1.00` e IGV 999, la respuesta era 201 ACEPTADO. Los importes eran `float`.

## Decisión

1. El contrato **prohíbe** los campos de impuestos y totales (`extra="forbid"` → 400 `ERR-CONTRATO-CAMPO-NO-PERMITIDO`). El cliente envía solo cantidad, unidad, valor unitario, afectación (Catálogo 07), configuración del ISC (Catálogo 08) y si la línea lleva ICBPER.
2. `Linea.calcular` y `Totales.de_lineas` calculan con `decimal.Decimal` y redondeo mitad hacia arriba a 2 decimales:
   - **ISC 01** = valor de venta × tasa;
   - **ISC 02** = cantidad × monto fijo;
   - **ISC 03** = (cantidad × precio sugerido × 0.847) × tasa;
   - **IGV** = 18 % × (valor de venta + ISC), solo si la afectación es 10;
   - **ICBPER** = cantidad × tasa del año (S/ 0.50 desde 2023), solo en unidad NIU;
   - **importe total** = valor de venta + ISC + IGV + ICBPER.
3. La API devuelve los importes como cadenas decimales (`"359.90"`) para no perder precisión en JSON.

## Consecuencias

- El sistema es la fuente de verdad de los montos que van al XML y al PLE 14.1.
- Fuera de alcance (se rechazan con 422): las operaciones gratuitas, los anticipos y los descuentos globales. Se agregan extendiendo el mismo dominio.
