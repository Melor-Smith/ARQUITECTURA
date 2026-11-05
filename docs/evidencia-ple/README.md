# Validación de los TXT con el programa PLE oficial de SUNAT

| Dato | Valor |
|---|---|
| Fecha | 05/11/2026 |
| Programa | **PLE 5.2.0.7** (Programa de Libros Electrónicos de SUNAT), opción *Validar Libros Electrónicos*, en modo de prueba (sin clave SOL) |
| RUC | `20556677884`, el de ABC Software Corp en el caso |
| Archivo validado | [`docs/ejemplos/ple-12.1-LE2055667788420261000120100001111.txt`](../ejemplos/ple-12.1-LE2055667788420261000120100001111.txt), generado por `python scripts/generar_ejemplos.py` y validado **sin editarlo a mano** |

## Resultado

**[Constancia SUNAT: "Reporte de información consistente"](constancia-sunat-12.1-sin-errores.pdf)** para el formato 12.1, Registro del Inventario Permanente en Unidades Físicas, periodo octubre de 2026.

Los totales de control que calculó el PLE coinciden con el archivo:

| Total de control | Constancia SUNAT | Calculado del TXT |
|---|---:|---:|
| Entradas de unidades físicas | 11,270.00 | 11270.00 |
| Salidas de unidades físicas | -674.00 | -674.00 |
| Filas con estado 1 | 23 | 23 |
| Filas validadas | 23 | 23 |

## Cómo se llegó: tres rondas

La validación oficial encontró dos reglas que el Excel del Anexo 2 no deja explícitas o que el sistema no aplicaba. Se corrigieron en el **dominio**, no editando el TXT, y cada una quedó con su prueba.

| Ronda | Resultado del PLE | Causa | Corrección | Prueba |
|:-:|---|---|---|---|
| 1 | 23 errores, columna 16: "El valor no se encontró en la tabla de parámetros" | La unidad iba con los códigos numéricos de la tabla 6 anterior (`01`, `07`) | El campo 16 usa el código **UN/ECE** (`KGM`, `NIU`), el mismo del Catálogo 03 del XML | `test_unidad_con_codigo_numerico_de_la_tabla_6_anterior_se_rechaza` |
| 2 | 4 errores, columna 11: "Tipo de documento no válido para tipo de operación efectuada" | Ventas y compras (operaciones 01 y 02) sustentadas solo con un vale, una guía interna o "s/n" (documento `00`) | Si no hay comprobante ni guía de remisión, el movimiento se anota como operación **99 (Otros)**: la venta sigue *pendiente de facturar* y queda una observación. Pedir explícitamente 01 a 06 con un documento `00` se rechaza con `ERR-KARDEX-DOCUMENTO-OPERACION` | `test_venta_o_compra_con_documento_interno_se_rechaza`, `test_venta_con_vale_y_operacion_01_explicita_se_rechaza`, `test_venta_con_documento_interno_se_rechaza` |
| 3 | **Sin errores** | — | — | `test_inventario_121_cumple_el_anexo_2` |

Desde entonces, el validador propio (`src/domain/ple_estructura.py`) aplica también estas dos reglas, así que detecta esos errores antes de llegar a SUNAT.

## Registro de Ventas 14.1

El PLE 5.2.0.7 trae como corte `PER_CORTE_RVIE_TODOS = 20220400`:

- desde el periodo **abril de 2022**, el Registro de Ventas ya no se presenta por el PLE, sino por el **RVIE / SIRE**;
- con un 14.1 de un periodo posterior y sin clave SOL, el programa no inicia la validación y no muestra ningún mensaje.

Es un límite de la norma vigente, no del generador. El TXT 14.1 se verifica contra el Excel oficial del Anexo 2 (`tests/unit/ple/`). La prueba en el PLE con un periodo anterior al corte está preparada y pendiente de ejecutar.

## Cómo repetir la validación

1. Instale el PLE desde el [portal de SUNAT](https://emprender.sunat.gob.pe/comprobantes-libros/registros-libros-electronicos/programa-libros-electronicos-ple).
2. Ingrese con **"Sin clave SOL (modo de prueba)"** y el RUC `20556677884`.
3. Entre a **Validar**, use **Añadir archivo** para cargar el TXT de `docs/ejemplos/` y pulse **Validar**.
4. Abra **Ver constancia**.
