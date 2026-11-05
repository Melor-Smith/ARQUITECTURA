# Validación de los TXT con el programa PLE oficial de SUNAT

| Dato | Valor |
|---|---|
| Fecha | 05/11/2026 |
| Programa | **PLE 5.2.0.7** (Programa de Libros Electrónicos de SUNAT), opción *Validar Libros Electrónicos*, en modo de prueba (sin clave SOL) |
| RUC | `20556677884`, el de ABC Software Corp en el caso |
| Archivo validado | [`paquete/12.1-octubre-2026/LE2055667788420261000120100001111.TXT`](paquete/12.1-octubre-2026/LE2055667788420261000120100001111.TXT), generado por el sistema y validado **sin editarlo a mano** |
| Huella SHA-256 | `589d39b5490cecb15c88c77f1a19b62fa4235bdc9f004cf579355f5e1c3edb6b`. Una prueba exige que el sistema siga generando exactamente este archivo (`test_el_12_1_es_el_mismo_que_valido_sunat`) |

## Resultado

**[Constancia SUNAT: "Reporte de información consistente"](constancia-sunat-12.1-sin-errores.pdf)** para el formato 12.1, Registro del Inventario Permanente en Unidades Físicas, periodo octubre de 2026.

Los totales de control que calculó el PLE coinciden con el archivo:

| Total de control | Constancia SUNAT | Calculado del TXT |
|---|---:|---:|
| Entradas de unidades físicas | 11,270.00 | 11270.00 |
| Salidas de unidades físicas | -674.00 | -674.00 |
| Filas con estado 1 | 23 | 23 |
| Filas validadas | 23 | 23 |

## Paquete reproducible

Todo lo que se cargó en el PLE está en [`paquete/`](paquete) y se regenera con:

```bash
python scripts/preparar_validacion_ple.py
```

| Carpeta | Archivos | Origen |
|---|---|---|
| [`12.1-octubre-2026/`](paquete/12.1-octubre-2026) | 12.1 | Sistema. Es el archivo validado **sin inconsistencias** |
| [`14.1-octubre-2026/`](paquete/14.1-octubre-2026) | 14.1 + 8.1 y 8.2 sin información (archivos vacíos) | Sistema |
| [`14.1-marzo-2022/`](paquete/14.1-marzo-2022) | 14.1 + 8.1 con una compra + 8.2 vacío | 14.1: sistema, con reloj e inventario inicial en marzo de 2022. 8.1: **insumo de prueba** (el sistema no lleva compras, pero el PLE exige presentarlas junto al 14.1) |

`tests/integration/test_paquete_validacion_ple.py` comprueba:

- que el paquete versionado es exactamente lo que genera el script;
- que cada TXT cumple el Anexo 2;
- que ventas y compras van juntas, como exige el PLE.

## Cómo se llegó: tres rondas

La validación oficial encontró dos reglas que el Excel del Anexo 2 no deja explícitas o que el sistema no aplicaba. Se corrigieron en el **dominio**, no editando el TXT, y cada una quedó con su prueba.

| Ronda | Resultado del PLE | Causa | Corrección | Prueba |
|:-:|---|---|---|---|
| 1 | 23 errores, columna 16: "El valor no se encontró en la tabla de parámetros" | La unidad iba con los códigos numéricos de la tabla 6 anterior (`01`, `07`) | El campo 16 usa el código **UN/ECE** (`KGM`, `NIU`), el mismo del Catálogo 03 del XML | `test_unidad_con_codigo_numerico_de_la_tabla_6_anterior_se_rechaza` |
| 2 | 4 errores, columna 11: "Tipo de documento no válido para tipo de operación efectuada" | Ventas y compras (operaciones 01 y 02) sustentadas solo con un vale, una guía interna o "s/n" (documento `00`) | Si no hay comprobante ni guía de remisión, el movimiento se anota como operación **99 (Otros)**: la venta sigue *pendiente de facturar* y queda una observación. Pedir explícitamente 01 a 06 con un documento `00` se rechaza con `ERR-KARDEX-DOCUMENTO-OPERACION` | `test_venta_o_compra_con_documento_interno_se_rechaza`, `test_venta_con_vale_y_operacion_01_explicita_se_rechaza`, `test_venta_con_documento_interno_se_rechaza` |
| 3 | **Sin errores** | — | — | `test_inventario_121_cumple_el_anexo_2` |

Desde entonces, el validador propio (`src/domain/ple_estructura.py`) aplica también estas dos reglas, así que detecta esos errores antes de llegar a SUNAT.

## Registro de Ventas 14.1: no se puede validar en modo de prueba

Se intentó cinco veces con el mismo PLE 5.2.0.7:

| Intento | Archivos | Resultado |
|:-:|---|---|
| 1 | 14.1 + 8.1 + 8.2 de octubre de 2026 (compras sin información) | El PLE no hace nada y no muestra ningún mensaje |
| 2 | Lo mismo, con periodo marzo de 2022, antes del corte del RVIE | El PLE no hace nada |
| 3 | Solo el 14.1 de marzo de 2022 | Aviso: *"…se deben presentar ambos según la combinación (080100, 080200 y 140100)…"*. Esto confirma que el programa procesa la solicitud |
| 4 | 14.1 + **8.1 con una compra real** (factura 0001-4587, 42 campos) + 8.2 vacío, de marzo de 2022 | El PLE no hace nada |
| 5 | Lo mismo que en el intento 4, generado por el sistema, con "Detallada" y el componente `PLEAccelerator` activo; se monitorearon procesos, red y archivos | El PLE no hace nada (ver abajo) |

En los intentos 2 a 4 se usó una copia del 14.1 con el periodo y las fechas cambiados a mano. Hoy el sistema genera ese 14.1 directamente (`paquete/14.1-marzo-2022/`), con seis comprobantes, porque la factura del vale necesita fichas de 2026.

En los intentos 1, 2 y 4 el PLE **no creó su carpeta de trabajo ni dejó registro en su bitácora** (`plelog.db3`). Con el 12.1, en cambio, sí lo hizo. Es decir, se detiene **antes de leer los archivos**, así que el resultado no depende del contenido de los TXT.

**Qué se midió en el intento 5.** El código fuente de la pantalla *Validar*, que viene en la instalación (`componentes/sunat/ple/ValidarPanel.mxml.bak`), muestra que los registros de compras y ventas no se validan en la ventana. Se envían por TCP a `PLEAccelerator.exe` (`127.0.0.1:1977`), que tiene las funciones `f140100d` y `f140100g`. Durante 4 minutos se registró la actividad de ambos procesos:

- el PLE y el acelerador se comunican sin errores: hubo más de 160 conexiones, una cada 2 segundos, todas cerradas con normalidad;
- al pulsar *Validar* no aparece ningún trabajo nuevo, no se crea la carpeta de trabajo y no se escribe ningún archivo.

El bloqueo ocurre en el PLE, antes de leer los TXT, y no en el contenido del 14.1.

La explicación más probable es la siguiente. El registro de compras y el de ventas se validan juntos en un flujo propio: genera las casillas para el PDT y usa datos que el PLE obtiene de SUNAT al ingresar con clave SOL (`LIST_PADRON154`, `gIndOkSoloRVIE`, corte `PER_CORTE_RVIE_TODOS = 20220400`). En modo de prueba, con un RUC ficticio, esos datos no existen. Además, desde abril de 2022 el Registro de Ventas se presenta por el **RVIE / SIRE**, no por el PLE.

**Cómo está verificado entonces el 14.1:**

- contra el Excel oficial del Anexo 2, campo por campo (`tests/unit/ple/test_anexo2_oficial.py`);
- con las reglas entre campos del Anexo 2 (`tests/unit/ple/test_txt_registro_ventas.py`);
- de extremo a extremo con todos los comprobantes de ejemplo (`test_registro_de_ventas_141_cumple_el_anexo_2`);
- **contra lo que SUNAT aceptó:** cada una de las siete filas del 14.1 coincide campo por campo con el XML que el servicio beta de SUNAT aceptó con CDR código 0 ([evidencia](../evidencia-sunat/README.md)). Los campos comparados son el tipo y número de documento del cliente, la base gravada, el IGV, el ISC, el ICBPER y el importe total, con signo negativo en la nota de crédito (`test_cada_fila_del_14_1_cuadra_con_el_comprobante_que_sunat_acepto`).

Para validarlo también en el PLE hace falta un RUC real con clave SOL. Ese paso queda pendiente, fuera del alcance del caso académico.

## Cómo repetir la validación

1. Instale el PLE desde el [portal de SUNAT](https://emprender.sunat.gob.pe/comprobantes-libros/registros-libros-electronicos/programa-libros-electronicos-ple).
2. Ingrese con **"Sin clave SOL (modo de prueba)"** y el RUC `20556677884`.
3. Entre a **Validar** y use **Añadir archivo** para cargar **todos los archivos de una carpeta** de [`paquete/`](paquete).
4. Pulse **Validar** y abra **Ver constancia**.
