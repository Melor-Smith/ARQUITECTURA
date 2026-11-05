# 1. El caso ABC Software Corp: brechas, decisiones y riesgos

## 1.1 Situación de partida

ABC Software Corp distribuye abarrotes al por mayor y menor. Entre sus productos hay bebidas alcohólicas y gaseosas (afectas al ISC) y entrega bolsas plásticas (afectas al ICBPER). Vende al contado y al crédito a bodegas y distribuidores.

Su almacén funciona con un software básico que guarda fichas de cinco campos: `fecha`, `ingreso`, `salida`, `producto` y `nro_documento`. Ese registro es un Kardex informal: no permite emitir comprobantes electrónicos ni llevar los libros que exige SUNAT.

## 1.2 Brechas y cómo se cierran

Cada brecha está enlazada con lo que la cierra en el sistema y con la prueba que lo demuestra.

| # | Brecha del sistema actual | Consecuencia | Cómo la cierra el sistema | Evidencia |
|---|---|---|---|---|
| B1 | No emite comprobantes electrónicos | Incumple la RS 097-2012 (SEE) | Emisión de factura, boleta y notas de crédito y débito en UBL 2.1, firmadas y enviadas a una OSE | `POST /api/v1/comprobantes`; `tests/unit/generacion_xml/` |
| B2 | No valida RUC ni documentos | Facturas a RUC inexistentes o mal digitados | `Ruc` con prefijo y módulo 11; `DocumentoIdentidad` según el Catálogo 06 | `tests/unit/test_valores.py::TestRuc` |
| B3 | Impuestos calculados a mano o por el vendedor | Diferencias entre lo cobrado y lo declarado | El dominio calcula IGV, ISC (Catálogo 08) e ICBPER con `Decimal`; el cliente no puede enviar montos | `tests/unit/test_tributos.py`; contraejemplo `i05` |
| B4 | Ventas al crédito sin registro formal | Incumple la RS 193-2020 (forma de pago) | `FormaPago` con cuotas que deben sumar el total | `tests/unit/test_letras_y_pagos.py` |
| B5 | Sin numeración controlada | Números repetidos o saltados | Correlativo asignado por el servidor de forma atómica, después de validar | `tests/integration/test_concurrencia.py` |
| B6 | Sin constancia de SUNAT | El comprobante "existe" aunque SUNAT no lo haya recibido | Estado según el CDR; 202 y reenvío si la OSE no responde | `TestOse` |
| B7 | Kardex informal | Incumple la RS 234-2006; no hay formato 12.1 | `Kardex` con saldo, tabla 5, tabla 10, tabla 12 y unidad de la tabla 6 | `TestInventario121` |
| B8 | Sin registro de ventas | No hay formato 14.1 | Libro 14.1 generado desde los comprobantes | `TestRegistroVentas141` |
| B9 | Fichas con fechas, glosas y documentos libres | Datos históricos inutilizables | Migración con homologación, clasificación de documentos, lotes con observaciones y conciliación | `TestLoteDeMigracion` |

## 1.3 Supuestos

| Supuesto | Efecto si es falso | Cómo validarlo |
|---|---|---|
| ABC emite desde un solo establecimiento (`0000`) | Habría que configurar las series por establecimiento | Revisar la ficha RUC de ABC |
| No hay operaciones gratuitas, anticipos ni detracciones | Esos casos se rechazan con 422 | Entrevista con el contador |
| La OSE devuelve el CDR de forma síncrona | Habría que agregar la consulta de ticket asíncrona | Documentación de la OSE elegida |
| El inventario inicial se puede contar físicamente al corte | Sin saldo inicial, el 12.1 no cuadra | Toma de inventario antes de migrar |
| Las glosas antiguas se pueden homologar con una tabla | Muchas fichas quedarían observadas | Ejecutar un lote de prueba y revisar las observaciones |

## 1.4 Riesgos

| Riesgo | Prob. | Impacto | Mitigación implementada |
|---|---|---|---|
| Cambio de una tasa o de un catálogo por SUNAT | Alta | Medio | Tasas y catálogos en un solo módulo del dominio (`tributos.py`, `catalogos.py`) |
| Rechazo de la OSE por un detalle del XML | Media | Alto | XML generado desde el XSD, validado antes y después de firmar; 77 pruebas de generación y regresión |
| Caída de la OSE en horario de venta | Media | Alto | La venta no se bloquea: 202 `PENDIENTE_ENVIO` y reenvío posterior |
| Doble emisión por reintentos de red | Media | Alto | `Idempotency-Key` |
| Migración con datos sucios | Alta | Medio | Lotes que no se detienen, fichas observadas y conciliación por producto |
| Divergencia entre documentación y código | Alta | Medio | El contrato OpenAPI y la matriz se generan desde el código y se verifican en CI |
| Fuga del certificado digital | Baja | Muy alto | El certificado nunca se versiona (`.gitignore`) y se carga por variable de entorno |
