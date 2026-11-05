# Especificación 001: Facturación electrónica UBL 2.1 e inventario permanente

- **Empresa:** ABC Software Corp, distribución mayorista y minorista de abarrotes. Vende bebidas con ISC y entrega bolsas plásticas, afectas al ICBPER.
- **Normativa:**
  - RS 097-2012/SUNAT y sus catálogos;
  - RS 234-2006/SUNAT (registros de inventario);
  - RS 286-2009/SUNAT (PLE);
  - Ley 30884 (ICBPER);
  - OASIS UBL 2.1.
- **Metodología:** spec-first. Esta especificación, los ejemplos de [`specs/ejemplos`](../ejemplos) y los DTO del contrato se escriben antes que la implementación. Cada escenario tiene una prueba automatizada (indicada debajo del escenario).

## Problema

El almacén operaba con un sistema básico de fichas (`fecha`, `ingreso`, `salida`, `producto`, `nro_documento`). Esas fichas:

1. no estaban enlazadas a comprobantes electrónicos;
2. no cumplían la RS 234-2006: faltaban establecimiento, tipo de existencia, tipo de operación, documento tipificado, unidad normalizada y saldo;
3. no permitían generar los libros 14.1 y 12.1;
4. no desglosaban el ISC (Catálogo 08) ni el ICBPER.

---

## HU-01: Emitir comprobantes (factura, boleta, nota de crédito y nota de débito)

**Como** facturador **quiero** enviar solo los datos comerciales de la venta **para que** el sistema calcule los tributos, numere, genere el XML UBL 2.1, lo firme y lo envíe a la OSE.

```gherkin
Característica: Emisión de comprobantes electrónicos

  Antecedentes:
    Dado el emisor configurado "ABC SOFTWARE CORP S.A.C." con RUC "20556677884"
    Y un token con el alcance "comprobantes:emitir"

  Escenario: Factura gravada; el servidor calcula y numera
    Cuando envío una factura (01) serie "F001" al cliente con RUC "20123456786"
      Y las líneas "50 KGM de arroz a 4.20" y "25 KGM de azúcar a 3.80" con afectación "10"
    Entonces la respuesta es 201 con Location "/api/v1/comprobantes/01/F001-1"
      Y el correlativo es 1, asignado por el servidor
      Y las gravadas son "305.00", el IGV "54.90" y el importe total "359.90"
      Y el estado es "ACEPTADO", tomado del CDR con código "0"
      Y el hash_cpe es el ds:DigestValue del XML firmado

  Escenario: Boleta con serie B
    Cuando envío una boleta (03) serie "B001" a un cliente con DNI "46027897"
    Entonces la respuesta es 201 con serie_numero "B001-1"

  Escenario: Serie alfanumérica y correlativo de 8 dígitos
    Dado que la serie "F001" ya usó hasta el número 12345677
    Cuando envío una factura serie "F001"
    Entonces el serie_numero es "F001-12345678"
      Y una factura con serie "FA01" también es aceptada

  Escenario: ISC de los tres sistemas del Catálogo 08 e ICBPER
    Cuando envío líneas con ISC sistema "01" (tasa 0.20), "02" (monto fijo 1.35) y "03" (tasa 0.17, precio sugerido 12.50)
      Y una línea de 3 bolsas con aplica_icbper
    Entonces el ISC calculado es "54.00", "16.20" y "7.20"
      Y el ICBPER es "1.50"
      Y el XML contiene cbc:TierRange "01", "02" y "03"

  Escenario: El cliente no puede enviar impuestos ni totales
    Cuando envío una línea con "igv_item": 999 y "totales": {"importe_total": 1}
    Entonces la respuesta es 400 application/problem+json con codigo "ERR-CONTRATO-CAMPO-NO-PERMITIDO"

  Esquema del escenario: Reglas SUNAT incumplidas
    Cuando envío <caso>
    Entonces la respuesta es <http> con codigo "<codigo>"
    Ejemplos:
      | caso                                            | http | codigo                        |
      | una factura con RUC "20123456780" (módulo 11)   | 422  | ERR-SUNAT-RUC                 |
      | una factura a un cliente con DNI                | 422  | ERR-SUNAT-RUC                 |
      | una factura con serie "B001"                    | 422  | ERR-SUNAT-SERIE               |
      | una boleta con serie "F001"                     | 422  | ERR-SUNAT-SERIE               |
      | un ISC con sistema "99"                         | 400  | ERR-SUNAT-CAT08               |
      | un ISC sistema "01" sin tasa                    | 422  | ERR-SUNAT-CAT08               |
      | una unidad "SACO" (fuera del Catálogo 03)       | 400  | ERR-SUNAT-CAT03               |
      | más kilos de los que hay en stock               | 422  | ERR-KARDEX-SALDO-INSUFICIENTE |

  Escenario: Un rechazo de negocio no consume correlativo
    Dado que una emisión fue rechazada con 422
    Cuando emito una factura válida
    Entonces su serie_numero es "F001-1"

  Escenario: Nota de crédito por devolución
    Dada la factura "F001-1" aceptada
    Cuando envío una nota de crédito (07) serie "FC01" con motivo "07" (Catálogo 09) por 10 KGM
    Entonces la respuesta es 201
      Y el Kardex registra una entrada de 10 KGM con tipo de operación "24"

  Escenario: Nota que excede el comprobante modificado
    Dada la factura "F001-1" por 359.90
    Cuando envío una nota de crédito por 500 KGM
    Entonces la respuesta es 422
```

Pruebas: `tests/acceptance/test_api_comprobantes.py` (clases `TestEmisionFeliz`, `TestSerieYCorrelativo`, `TestUnidadesUnece`, `TestCalculoDelegadoAlCliente`, `TestValidacionesSunat`, `TestNotas`).

## HU-02: Estado real ante la OSE

**Como** contador **quiero** que el estado del comprobante refleje el CDR **para** no declarar como aceptado algo que SUNAT no aceptó.

```gherkin
Característica: Envío a la OSE

  Escenario: OSE caída
    Dado que la OSE no responde
    Cuando emito una factura
    Entonces la respuesta es 202 con estado "PENDIENTE_ENVIO" y sin CDR
    Cuando reintento con POST ".../envios" y la OSE sigue caída
    Entonces la respuesta es 503 con cabecera Retry-After
    Cuando la OSE se recupera y reintento
    Entonces la respuesta es 200 con estado "ACEPTADO"
    Cuando reintento otra vez
    Entonces la respuesta es 409 "ERR-COMPROBANTE-YA-PROCESADO"

  Escenario: Respuesta ilegible de la OSE
    Dado que la OSE responde algo que no es un CDR
    Cuando reintento el envío
    Entonces la respuesta es 502

  Escenario: Rechazo
    Dado que la OSE rechaza el comprobante (CDR 2335)
    Entonces el estado es "RECHAZADO"
      Y el Kardex registra un movimiento compensatorio
      Y el comprobante no aparece en el Registro de Ventas 14.1
```

Pruebas: `TestOse`, `TestRegistroVentas141::test_comprobantes_rechazados_no_se_anotan`.

## HU-03: Idempotencia y seguridad

```gherkin
  Escenario: Reintento de red con la misma Idempotency-Key
    Cuando envío dos veces la misma factura con "Idempotency-Key: pedido-2026-0001"
    Entonces la primera respuesta es 201 y la segunda 200, ambas con "F001-1"
      Y no se crea un segundo comprobante

  Escenario: Clave reutilizada con otro contenido
    Entonces la respuesta es 409 "ERR-IDEMPOTENCIA-CONFLICTO"

  Escenario: Autenticación y autorización
    Sin token → 401 con WWW-Authenticate: Bearer
    Con el token "dev-consulta" en POST /comprobantes → 403 "ERR-AUTH-ALCANCE"
```

Pruebas: `TestIdempotencia`, `TestSeguridad`.

## HU-04: Migrar las fichas del sistema antiguo al inventario permanente

**Como** jefe de almacén **quiero** migrar las fichas informales **para** tener un inventario en unidades físicas conforme a la RS 234-2006 y facturar las salidas pendientes.

```gherkin
Característica: Migración de fichas del sistema antiguo

  Escenario: Vale de salida por venta
    Dada la ficha {fecha "2026-10-15", ingreso 0, salida 5, producto "Saco de Azúcar Rubia 50kg", nro_documento "VALE-SALIDA-0042"}
    Cuando la migro
    Entonces la respuesta es 201 con estado "PENDIENTE_FACTURACION"
      Y el Kardex de "AB-AZU-001" registra una salida de 250 KGM (5 sacos × 50, por homologación)
      Y el documento de soporte es tipo "00" (tabla 10), serie "VALE-SALIDA", número "0042"
      Y NO se asigna ni se sugiere un número de comprobante SUNAT

  Escenario: Guía interna de ingreso
    Dada una ficha con ingreso 20 de "Saco de Arroz Extra 50kg"
    Entonces se registra una entrada de 1000 KGM con tipo de operación "02" y estado "NO_REQUIERE_FACTURA"

  Esquema del escenario: Fichas inválidas
    Ejemplos:
      | ficha                                    | http | codigo                        |
      | ingreso 0 y salida 0                     | 422  | ERR-LEGADO-SIN-MOVIMIENTO     |
      | ingreso y salida a la vez                | 422  | ERR-LEGADO-AMBIGUA            |
      | glosa sin homologación                   | 422  | ERR-LEGADO-NO-HOMOLOGADO      |
      | salida mayor que el saldo                | 422  | ERR-KARDEX-SALDO-INSUFICIENTE |
      | el mismo nro_documento migrado dos veces | 409  | ERR-LEGADO-DUPLICADO          |
      | fecha "31/09/2026" (imposible)           | 422  | ERR-LEGADO-FECHA              |

  Escenario: Facturar un vale migrado
    Dado el vale "VALE-SALIDA-0042" migrado
    Cuando emito una factura con documentos_legado ["VALE-SALIDA-0042"] por 250 KGM de azúcar
    Entonces la migración pasa a "FACTURADA" con comprobante "01/F001-1"
      Y el XML lleva cac:AdditionalDocumentReference con ID "VALE-SALIDA-0042" y DocumentTypeCode "99"
      Y el Kardex no vuelve a descontar los 250 KGM
    Cuando intento facturar el mismo vale otra vez
    Entonces la respuesta es 409 "ERR-LEGADO-YA-FACTURADO"
```

Pruebas: `tests/acceptance/test_api_inventario_y_libros.py` (`TestMigracion`, `TestFacturacionDeValesLegado`).

## HU-05: Libros electrónicos

```gherkin
Característica: PLE

  Escenario: Registro de Ventas 14.1
    Dadas la factura F001-1 y la nota de crédito FC01-1 de octubre de 2026
    Cuando pido GET /api/v1/libros-electronicos/registro-ventas/202610
    Entonces recibo el archivo "LE2055667788420261000140100001111.txt"
      Y cada línea tiene 35 campos separados por "|"
      Y la nota de crédito figura con importe "-49.56" y referencia "01 | F001 | 1"

  Escenario: Inventario en unidades físicas 12.1
    Cuando pido GET /api/v1/libros-electronicos/inventario-unidades-fisicas/202610
    Entonces cada movimiento lleva establecimiento, tipo de existencia (tabla 5), documento (tabla 10),
      tipo de operación (tabla 12) y unidad UN/ECE ("KGM"), como exige el validador PLE 5.2.0.7

  Escenario: Venta sustentada solo con un vale del sistema antiguo
    Cuando migro una ficha de salida con nro_documento "VALE-SALIDA-0042" sin indicar tipo_operacion
    Entonces queda PENDIENTE_FACTURACION y en el 12.1 se anota como operación "99" con documento "00"
      Y si pido explícitamente tipo_operacion "01" la respuesta es 422 "ERR-KARDEX-DOCUMENTO-OPERACION"
```

Pruebas: `TestRegistroVentas141`, `TestInventario121`.

## HU-06: El contrato no diverge de la implementación

```gherkin
  Escenario: Contrato verificado
    Entonces specs/contracts/openapi.yaml es idéntico al OpenAPI generado por el código
      Y todos los ejemplos de specs/ejemplos son aceptados con 201
      Y todo error se documenta como application/problem+json
```

Pruebas: `tests/acceptance/test_contrato.py`.

## HU-07: Ventas al crédito (RS 193-2020)

```gherkin
Característica: Forma de pago en facturas

  Escenario: Factura al contado por defecto
    Cuando emito una factura sin forma_pago
    Entonces el XML lleva cac:PaymentTerms con PaymentMeansID "Contado"

  Escenario: Factura al crédito en dos cuotas
    Cuando emito una factura de 247.80 con forma_pago CREDITO y cuotas 123.90 (15/01/2027) y 123.90 (15/02/2027)
    Entonces el XML lleva PaymentMeansID "Credito" con Amount 247.80, "Cuota001" y "Cuota002" con su vencimiento
      Y el campo 5 del Registro de Ventas 14.1 queda vacío, porque la última cuota vence después del mes siguiente al periodo
        (el PLE solo acepta hasta ese día; el vencimiento queda en el XML)

  Escenario: Crédito que vence el mes siguiente
    Cuando emito una factura en octubre de 2026 con una sola cuota que vence el 20/11/2026
    Entonces el campo 5 del Registro de Ventas 14.1 es "20/11/2026"

  Escenario: Cuotas que no cuadran
    Cuando las cuotas suman 223.90 para un total de 247.80
    Entonces la respuesta es 422 "ERR-SUNAT-FORMA-PAGO"
```

Pruebas: `tests/unit/test_letras_y_pagos.py::TestFormaPago`, `test_forma_de_pago_credito_con_monto_pendiente_y_cuotas`; contraejemplo `i10`.

## HU-08: Migrar el archivo completo del sistema antiguo

```gherkin
Característica: Migración por lotes

  Escenario: Lote desordenado con datos sucios
    Dado el archivo specs/ejemplos/lote-fichas-legado.json con 9 fichas desordenadas, fechas en 5 formatos,
      una fecha imposible, una glosa sin homologar y un vale repetido
    Cuando lo envío a POST /api/v1/inventario/migraciones/lotes
    Entonces la respuesta es 201 con 6 migradas, 2 observadas y 1 duplicada
      Y "FACT 001-4587" se registra como factura (tabla 10 tipo 01, serie 0001)
      Y la salida con "B001-0000231" queda FACTURADA_EN_SISTEMA_ANTIGUO
      Y la conciliación del azúcar es 1000 − 300 = 700 y cuadra

  Escenario: Reprocesar el mismo archivo
    Cuando envío el mismo lote otra vez
    Entonces no se migra nada nuevo: 7 duplicadas y 2 observadas
```

Pruebas: `tests/acceptance/test_api_inventario_y_libros.py::TestLoteDeMigracion`.

## HU-09 (Taller 2): Generar el XML desde el XSD en el lenguaje del dominio

```gherkin
Característica: Generación del XML UBL 2.1

  Esquema del escenario: Cada escenario de negocio produce un XML conforme
    Dado el comprobante del dominio "<escenario>"
    Cuando el GeneradorUblXsdata lo serializa
    Entonces el XML valida contra el XSD oficial de OASIS
      Y es idéntico byte a byte a su XML de referencia
    Ejemplos:
      | escenario |
      | factura-contado | factura-credito | factura-completa | factura-exportacion-usd |
      | factura-de-vale | boleta | nota-credito | nota-debito |
```

Pruebas: `tests/unit/generacion_xml/` (92 pruebas). Detalle en [`docs/TALLER-2-generacion-xml.md`](../../docs/TALLER-2-generacion-xml.md).
