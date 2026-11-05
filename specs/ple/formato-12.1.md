# Formato 12.1: Registro del Inventario Permanente en Unidades Físicas (PLE)

- **Libro:** `120100`.
- **Endpoint:** `GET /api/v1/libros-electronicos/inventario-unidades-fisicas/{AAAAMM}?formato=txt|json`.
- **Implementación:** `Kardex` y `MovimientoInventario` ([`src/domain/inventario.py`](../../src/domain/inventario.py)); `FilaInventario121` e `inventario_121` ([`src/domain/libros.py`](../../src/domain/libros.py)).
- **Estructura:** `ESTRUCTURA_121` ([`src/domain/ple_estructura.py`](../../src/domain/ple_estructura.py)).
- **Prueba:** `TestInventario121`, `TestLineaDelInventario121`, `test_inventario_121_cumple_el_anexo_2` y `TestKardex`.

## Por qué el 12.1 y no el 13.1

La RS 234-2006 exige, según el nivel de ingresos, el inventario permanente en **unidades físicas** (12.1) o el **valorizado** (13.1). El sistema antiguo solo registra cantidades (`ingreso`, `salida`), así que es la materia prima natural del 12.1. El 13.1 requiere además costo unitario y método de valuación, que el sistema antiguo no tiene: queda fuera de alcance y se puede agregar como otro libro sobre el mismo `Kardex`.

## De la ficha del sistema antiguo al 12.1

| Ficha del sistema antiguo | Qué le faltaba | Cómo se completa |
|---|---|---|
| `producto` (texto libre) | Código de existencia y tipo de existencia (tabla 5) | Tabla de homologación → `Producto` (código, tabla 5, unidad Catálogo 03) |
| `ingreso` / `salida` | Unidad normalizada | Cantidad × factor de homologación (1 saco = 50 KGM); unidad del producto, con equivalencia a la tabla 6 |
| `ingreso` / `salida` | Tipo de operación (tabla 12) | Por defecto, 02 (compra) para ingresos y 01 (venta) para salidas; se puede indicar otro (11, 13, 21…) |
| `nro_documento` | Documento de soporte tipificado (tabla 10) | Tipo `00` (documento interno); serie y número separados por el último guion (`VALE-SALIDA` / `0042`) |
| — | Establecimiento | Código de establecimiento anexo (por defecto `0000`) |
| — | Saldo | El `Kardex` mantiene el saldo, impide los saldos negativos y exige orden cronológico |

## Movimientos que alimentan el Kardex

| Hecho | Tipo de operación (tabla 12) | Documento (tabla 10) |
|---|---|---|
| Inventario inicial | 16 saldo inicial | 00 |
| Ficha antigua de salida | 01 venta (u otro indicado) | 00 (vale) |
| Ficha antigua de ingreso | 02 compra (u otro indicado) | 00 (guía interna) |
| Factura o boleta **sin** vale antiguo | 01 venta | 01 / 03 |
| Factura o boleta **con** vale antiguo | — (la salida ya se registró con el vale; no se duplica) | — |
| Nota de crédito por devolución (Catálogo 09: 06 o 07) | 24 entrada por devolución del cliente | 07 |
| Comprobante rechazado por la OSE | 99 otros (movimiento compensatorio; nunca se borra) | el del comprobante |

## Archivo

`LE` + RUC + `AAAAMM00` + `120100` + `00` + `1` (empresa operativa) + `1`/`0` (con o sin información) + `1` (soles) + `1` (generado por PLE) + `.txt`. Ejemplo: `LE2055667788420261000120100001111.txt`.

Una línea por movimiento, campos separados por `|`, `|` final y CRLF; sin cabecera. Los campos 20 al 40 (libre utilización) no se usan, así que no se escriben ni sus separadores.

## Campos del TXT (Anexo 2, PLE 5.0: 19 campos)

| # | Campo | Tipo y longitud | Oblig. | Origen |
|---|---|---|:-:|---|
| 1 | Periodo (AAAAMM00) | Numérico 8 | Sí | Periodo solicitado |
| 2 | CUO | Texto hasta 40 (sin `&`) | Sí | `I` + AAAAMM + correlativo |
| 3 | Correlativo del asiento | Alfanumérico 2 a 10 (A, M o C) | Sí | `M` + n |
| 4 | Código de establecimiento anexo | Numérico 4 a 7 | Sí | `MovimientoInventario.establecimiento` |
| 5 | Código del catálogo utilizado (tabla 13) | Numérico 1 | Sí | `9` (catálogo propio) |
| 6 | Tipo de existencia (tabla 5) | Numérico 2 | Sí | `producto.tipo_existencia` |
| 7 | Código propio de la existencia | Alfanumérico hasta 24 | Sí | `producto.codigo` |
| 8 | Catálogo internacional (tabla 13: UNSPSC o GTIN) | Numérico 1 | No | vacío (*) |
| 9 | Código de la existencia en ese catálogo | Numérico hasta 128 | No | vacío (*) |
| 10 | Fecha de emisión del documento | DD/MM/AAAA | Sí | `documento.fecha` |
| 11 | Tipo de documento (tabla 10) | Numérico 2 | Sí | `documento.tipo` |
| 12 | Serie del documento | Alfanumérico hasta 20 | Sí | `documento.serie` (`0` si no existe) |
| 13 | Número del documento | Alfanumérico hasta 20 | Sí | `documento.numero` (`0` si no existe) |
| 14 | Tipo de operación (tabla 12) | Numérico 2 | Sí | `tipo_operacion` |
| 15 | Descripción de la existencia | Texto hasta 80 | Sí | `producto.descripcion` |
| 16 | Unidad de medida (**tabla 6**) | Alfanumérico hasta 3 | Sí | `producto.unidad.unidad_ple` |
| 17 | Entradas | Importe, positivo o `0.00` | Sí | `entrada` |
| 18 | Salidas | Importe, **negativo** o `0.00` | Sí | `−salida` |
| 19 | Estado de la operación | `1`, `8` o `9` | Sí | `1` |

(*) Desde el 1/1/2021, los campos 8 y 9 son obligatorios solo si el comprobante electrónico consignó un código UNSPSC o GTIN. Este sistema no los emite en el XML, así que van vacíos. Si se agregan al producto, basta llenarlos en `inventario_121`.

Reglas entre campos que se validan: 17 y 18 son excluyentes; si hay campo 9, el 8 es obligatorio.

El **saldo final** de cada movimiento no forma parte del TXT, pero sí del formato impreso: lo entregan la vista JSON (`?formato=json`) y `GET /api/v1/inventario/kardex/{codigo}`.

> **Validación.** La estructura está en [`src/domain/ple_estructura.py`](../../src/domain/ple_estructura.py) y se contrasta automáticamente con el Excel oficial del Anexo 2 ([`anexo2/estructuras-ple-5.0.xls`](anexo2/estructuras-ple-5.0.xls)) en `tests/unit/ple/test_anexo2_oficial.py`. Ver [ADR 0010](../adr/0010-estructura-ple-en-el-dominio-validada-contra-el-anexo-2.md).
