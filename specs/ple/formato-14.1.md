# Formato 14.1: Registro de Ventas e Ingresos (PLE)

- **Libro:** `140100`.
- **Endpoint:** `GET /api/v1/libros-electronicos/registro-ventas/{AAAAMM}?formato=txt|json`.
- **Implementación:**
  - recorrido de los comprobantes del repositorio y armado de cada fila: `registro_ventas_141` y `FilaRegistroVentas141` ([`src/domain/libros.py`](../../src/domain/libros.py));
  - estructura, formato y validación de cada campo: `ESTRUCTURA_141`, `contenido_txt` ([`src/domain/ple_estructura.py`](../../src/domain/ple_estructura.py));
  - respuesta HTTP: [`vistas/ple.py`](../../src/adapters/inbound/http/vistas/ple.py).
- **Fuente normativa:** Anexo 2 de la RS 286-2009/SUNAT, PLE 5.0, en [`anexo2/estructuras-ple-5.0.xls`](anexo2/estructuras-ple-5.0.xls).
- **Pruebas:**
  - contraste con el Excel oficial: `tests/unit/ple/test_anexo2_oficial.py`;
  - formato, reglas y contraejemplos: `tests/unit/ple/test_txt_registro_ventas.py`;
  - extremo a extremo con todos los ejemplos: `tests/acceptance/test_ple_extremo_a_extremo.py`.

## Flujo

```
repositorio de comprobantes ──► registro_ventas_141 ──► FilaRegistroVentas141 (valores del dominio)
  (GenerarRegistroVentas141)     filtra el periodo,        │
                                 excluye RECHAZADOS,       ▼
                                 ordena, convierte a S/   contenido_txt: formatea cada campo según su tipo,
                                                           valida los 35 campos y las reglas entre campos,
                                                           une con "|", agrega "|" final y CRLF
                                                           │
                                                           ▼
                                                  TXT (o 422 ERR-PLE-ESTRUCTURA si algo incumple)
```

El sistema **no entrega un TXT que el PLE rechazaría**: si una fila incumple el Anexo 2, la respuesta es 422 con la línea, el campo y el motivo.

## Archivo

Según la hoja "Reglas de nombres de libros" del Anexo 2: `LE` + RUC + `AAAAMM` + `00` (día) + `140100` + `00` (oportunidad) + **O** `1` (empresa operativa) + **I** `1`/`0` (con o sin información) + **M** `1` (soles) + **G** `1` (generado por PLE) + `.txt`.

- Con operaciones: `LE2055667788420261000140100001111.txt`.
- Sin operaciones: `LE2055667788420261000140100001011.txt`. La versión anterior ponía aquí `0` en la posición O, que significa "cierre de operaciones, baja del RUC". Se corrigió.

## Reglas del TXT

| Regla del Anexo 2 | Cómo se cumple |
|---|---|
| Campos separados por `\|`, con `\|` al final de cada línea | `linea_txt` |
| Sin cabecera; una línea por comprobante | `contenido_txt`; un libro vacío es un archivo vacío |
| Fin de línea | CRLF (`\r\n`) |
| Fecha `DD/MM/AAAA` | `formatear` para el tipo `FECHA` |
| Importe: hasta 12 enteros y 2 decimales, punto, sin miles; negativo `-#.##` | Redondeo `ROUND_HALF_UP`; nunca `-0.00` |
| Tipo de cambio `#.###` | 3 decimales |
| Texto sin `\|`, `/` ni `\` | Se reemplazan por espacio; la razón social se corta a 100 caracteres |
| Alfanumérico: letras, dígitos y `( ) , . -` | Se quitan las tildes y se reemplaza lo demás por `-` |
| Campo sin dato | Vacío entre separadores (`\|\|`), nunca un espacio |
| Campos 36 al 70 (libre utilización) | No se usan, así que no se escriben ni sus separadores |

## Campos (35)

| # | Campo | Tipo y longitud | Oblig. | Origen en el sistema |
|---|---|---|:-:|---|
| 1 | Periodo (AAAAMM00) | Numérico 8 | Sí | Periodo solicitado |
| 2 | CUO | Texto hasta 40 (sin `&`) | Sí | `V` + AAAAMM + correlativo de 6 dígitos |
| 3 | Correlativo del asiento | Alfanumérico 2 a 10 (A, M o C) | Sí | `M` + n |
| 4 | Fecha de emisión | DD/MM/AAAA | No* | `Comprobante.fecha_emision` |
| 5 | Fecha de vencimiento o de pago | DD/MM/AAAA | No | Vencimiento de la última cuota **solo si cae hasta el último día del mes siguiente al periodo** (regla del PLE); si no, vacío |
| 6 | Tipo de comprobante (tabla 10) | Numérico 2 | Sí | `tipo` (01, 03, 07, 08) |
| 7 | Serie | Alfanumérico hasta 20 | Sí | `numero.serie` |
| 8 | Número | Alfanumérico hasta 20 | Sí | `numero.correlativo` (sin ceros a la izquierda) |
| 9 | Número final (consolidado) | Numérico hasta 20 | No | vacío (se anota cada comprobante) |
| 10 | Tipo de documento del cliente (tabla 2) | Alfanumérico 1 | No* | `cliente.documento.tipo`; **vacío** en boleta a cliente no identificado (el PLE no acepta `0`) |
| 11 | Número de documento del cliente | Alfanumérico hasta 15 | No* | `cliente.documento.numero`; vacío en el mismo caso |
| 12 | Apellidos y nombres o razón social | Texto hasta 100 | No* | `cliente.nombre` |
| 13 | Valor facturado de la exportación | Importe | No | `totales.exportacion` |
| 14 | Base imponible de la operación gravada | Importe | No | `totales.gravadas` (sin ISC, nota 4 del Anexo 2) |
| 15 | Descuento de la base imponible | Importe | No | 0.00 |
| 16 | IGV e IPM | Importe | No | `totales.igv` |
| 17 | Descuento del IGV | Importe | No | 0.00 |
| 18 | Operación exonerada | Importe | No | `totales.exoneradas` |
| 19 | Operación inafecta | Importe | No | `totales.inafectas` |
| 20 | ISC | Importe | No | `totales.isc` |
| 21 | Base imponible gravada con IVAP | Importe | No | 0.00 |
| 22 | IVAP | Importe | No | 0.00 |
| 23 | ICBPER | Importe | No* | `totales.icbper` (0.00 por defecto) |
| 24 | Otros tributos y cargos | Importe | No | 0.00 |
| 25 | Importe total | Importe | No | `totales.importe_total` |
| 26 | Moneda (tabla 4) | Alfanumérico 3 | No | `moneda` |
| 27 | Tipo de cambio | `#.###` | No* | `tipo_cambio` o 1.000 |
| 28 | Fecha del comprobante modificado | DD/MM/AAAA | No* | `referencia.fecha_emision` |
| 29 | Tipo del comprobante modificado | Numérico 2 | No* | `referencia.tipo` |
| 30 | Serie del comprobante modificado **o** código de la dependencia aduanera | Alfanumérico hasta 20 | No* | `referencia.numero.serie` |
| 31 | Número del comprobante modificado **o** número de la DUA | Alfanumérico hasta 20 | No* | `referencia.numero.correlativo` |
| 32 | Identificación del contrato o proyecto | Texto hasta 12 | No | vacío (no hay contratos de colaboración) |
| 33 | Error tipo 1: inconsistencia en el tipo de cambio | Numérico 1 | No | vacío |
| 34 | Indicador de comprobante cancelado con medio de pago | Numérico 1 | No | vacío (el sistema no registra el medio de pago) |
| 35 | Estado de la anotación | `0`, `1`, `2`, `8` o `9` | Sí | `1` (corresponde al periodo) |

\* Obligatorio según condiciones; estas son las que se validan en `_reglas_141`:

- 4, salvo anulados (35 = 2);
- 5 no puede pasar del mes siguiente;
- 10 no acepta `0` en boletas;
- 23 en los tipos 01, 03, 07 y 08;
- 27 si hay moneda;
- 28 a 31 en notas (07, 08, 87, 88).

El importe total cuadra: 13 + 14 + 16 + 18 + 19 + 20 + 23 = 25. Las notas de crédito van en negativo y los montos en USD se convierten a soles con el tipo de cambio del comprobante.

## Contraste con la estructura de 36 columnas propuesta para el taller

La plantilla que se usó como enunciado lista **36** columnas. El Anexo 2 oficial tiene **35**. Si se generara el TXT con esa plantilla, el PLE lo rechazaría, porque `validar_linea` exige exactamente 35 campos (prueba `test_estructura_de_36_columnas_no_es_la_del_anexo_2`).

| Plantilla del enunciado | Anexo 2 oficial | Consecuencia |
|---|---|---|
| 30 "Serie del comprobante modificado" y 31 "Código de dependencia aduanera" como dos campos | Un solo campo 30: serie **o** código de la dependencia aduanera | La plantilla agrega una columna y corre todos los campos desde el 31 |
| 32 "Número del comprobante modificado" | Campo 31 | — |
| 33 "Identificador de contrato", hasta 20 | Campo 32, **hasta 12**, de tipo texto | Se aceptaría un contrato demasiado largo |
| 35 "Indicador de comprobante (1 = mes, 8 = mes anterior, 9 = corrección)" | Esos valores pertenecen al campo **35, Estado** | Confunde el indicador con el estado |
| 36 "Estado (identifica medio de pago)" | El medio de pago es el campo **34**, y el estado es el **35** | Indicador y estado intercambiados |
| Campo 9 "Numérico" | Numérico, solo para tipos 00, 03, 12, 13 y 87 | Se valida |
| Campo 10 "6 = RUC, 1 = DNI" | Tabla 2; vacío (no `0`) en boleta sin identificar | Se valida |

Las reglas generales de la plantilla (pipe final, sin cabecera, `DD/MM/AAAA`, punto decimal, `||` para vacíos, CRLF) sí coinciden con el Anexo 2 y están implementadas.

> **Pendiente fuera del código:** cargar un TXT generado en el programa PLE de SUNAT (validador de escritorio). La estructura ya se verifica contra el Excel oficial, pero el programa aplica además validaciones contra el padrón RUC y sus propias tablas.
