# 5. Benchmark de soluciones de facturación electrónica

> **Estado: en curso.** Ninguna celda de un proveedor se llena de memoria. Cada dato se verifica en el sitio o en la cuenta DEMO del proveedor, y se anota la fuente y la fecha de consulta. Una celda sin verificar dice "por verificar".

## Método

1. **Fuentes admitidas:**
   - la página oficial del proveedor o de SUNAT;
   - la documentación de su API;
   - la cuenta DEMO (con captura en [`nubefact-demo/`](nubefact-demo/README.md)).
2. Cada celda lleva su fuente entre corchetes, por ejemplo `Sí [N1]`, y la lista de fuentes va al final con la URL y la fecha de consulta.
3. La última columna no compara: dice qué decidió ABC y dónde está en este repositorio.

## Comparación

| Capacidad | Nubefact | SEE-SOL / App Emprender (SUNAT) | Facturador SUNAT (SFS) | OpenUBL | Decisión para ABC |
|---|---|---|---|---|---|
| Emisión de factura, boleta y notas | por verificar | por verificar | por verificar | por verificar | Las cuatro, con XML generado desde el XSD y aceptado por SUNAT beta ([evidencia](../evidencia-sunat/README.md)) |
| Integración con inventario | por verificar | por verificar | por verificar | por verificar | Kardex en unidades físicas en el mismo núcleo; la venta mueve el stock y el rechazo lo revierte |
| Operación sin internet | por verificar | por verificar | por verificar | por verificar | 202 `PENDIENTE_ENVIO` y reenvío; MSI con API local en cada caja ([ADR 0008](../../specs/adr/0008-distribucion-msi-y-apk.md)) |
| API para integrarse | por verificar | por verificar | por verificar | por verificar | REST con contrato escrito primero: OpenAPI 3.1 y JSON Schemas ([ADR 0013](../../specs/adr/0013-contrato-escrito-primero-y-verificado-contra-el-codigo.md)) |
| Libros PLE | por verificar | por verificar | por verificar | por verificar | 14.1 y 12.1 generados desde los comprobantes y el Kardex; el 12.1 validado con el programa PLE ([evidencia](../evidencia-ple/README.md)) |
| Anulación (baja / resumen diario) | por verificar | por verificar | por verificar | por verificar | Contrato especificado, implementación pendiente ([ADR 0014](../../specs/adr/0014-comunicacion-de-baja-y-resumen-diario.md)) |
| Migración del sistema antiguo | por verificar | por verificar | por verificar | por verificar | Fichas por lotes con observaciones y conciliación ([ADR 0009](../../specs/adr/0009-migracion-por-lotes-y-clasificacion-de-documentos.md)) |
| Costo | por verificar | por verificar | por verificar | por verificar | Desarrollo propio con licencia MIT; costo de operación: servidor y certificado digital |

## Conclusiones

Se escriben cuando la tabla esté completa. Cada conclusión cita las celdas que la sostienen y dice qué caso de uso de [`03-casos-de-uso.md`](03-casos-de-uso.md) confirma o descarta (columna **Fuente**, código B).

## Fuentes

| ID | Fuente | URL | Fecha de consulta |
|---|---|---|---|
| N1 | | | |
