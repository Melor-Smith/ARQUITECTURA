# Especificación BDD y Tabla de Match Normativa (SDD)
## Empresa: ABC Software Corp
### Giro de Negocio: Comercialización de Abarrotes y Mercadería al Por Mayor y Menor
### Normativa: SUNAT RS N° 097-2012, RS N° 234-2006 y Estándar OASIS UBL-Invoice-2.1.xsd

---

## 1. Contexto de Negocio y Problemática Operativa

**ABC Software Corp** es una empresa dedicada a la distribución mayorista y minorista de abarrotes (arroz, azúcar, fideos, aceites, bebidas alcohólicas y gaseosas gravadas con ISC, y bolsas plásticas gravadas con ICBPER). 

Históricamente, su almacén central operaba con un software de fichas informales con campos mínimos no estructurados:
* `fecha`: Fecha manual del movimiento de inventario.
* `ingreso`: Unidades que entran por reposición o compras a proveedores.
* `salida`: Unidades despachadas a clientes o distribuidores.
* `producto`: Descripción libre del artículo (sin código de barras ni clasificador SUNAT).
* `nro_documento`: Identificador interno informal (ejemplo: `VALE-SALIDA-0042`, `GUIA-INT-0015`).

**Problema:**
1. Las salidas no estaban enlazadas a comprobantes de pago electrónicos con valor tributario ante SUNAT.
2. Incumplimiento de la **Resolución de Superintendencia N° 097-2012/SUNAT** (obligatoriedad de facturación electrónica bajo estándar OASIS UBL 2.1).
3. Incumplimiento de la **Resolución de Superintendencia N° 234-2006/SUNAT** sobre libros y registros vinculados a asuntos tributarios (Registro de Inventario Permanente Valorizado - Kardex Formal).
4. Omisión en el desglose de tributos especiales como el Impuesto Selectivo al Consumo (ISC - Catálogo 08) en licores/gaseosas y del Impuesto al Consumo de Bolsas de Plástico (ICBPER).

---

## 2. TABLA DE MATCH NORMATIVA: LEGADO <-> SUNAT PERÚ <-> OASIS UBL-Invoice-2.1.xsd

Esta tabla formal de homologación técnica y tributaria constituye el contrato de transformación entre los registros informales del almacén de ABC Software Corp, el modelo canónico tributario de SUNAT Perú, y los nodos del estándar internacional OASIS UBL 2.1:

| Campo Sistema Legado ABC Software Corp | Nombre en Modelo SUNAT Perú | Nodo / XPath exacto en OASIS UBL-Invoice-2.1.xsd | Catálogo / Regla Normativa SUNAT | Ejemplo Real de Negocio |
| :--- | :--- | :--- | :--- | :--- |
| `nro_documento` (cuando es salida comercial) | **`serie_numero`** | `/Invoice/cbc:ID` | **Regla SUNAT Serie-Número**: Serie `F` + 3 alfanuméricos (`F001`) guion y correlativo de hasta 8 dígitos (`000001`). Catálogo 01 (Código `01` = Factura). | `F001-000001` |
| `nro_documento` (como trazabilidad de origen) | `nro_documento_legado_origen` | `/Invoice/cac:DespatchDocumentReference/cbc:ID` | **RS N° 097-2012 / RS N° 234-2006**: Trazabilidad obligatoria de guía/vale de salida de almacén al comprobante de pago. | `VALE-SALIDA-0042` |
| `fecha` | `fecha_emision` | `/Invoice/cbc:IssueDate` | Formato ISO 8601 `YYYY-MM-DD`. Debe ser consistente con el período tributario y fecha de despacho. | `2026-10-22` |
| *(Hora de emisión del sistema)* | `hora_emision` | `/Invoice/cbc:IssueTime` | Formato ISO 8601 `hh:mm:ss`. Requerido en SUNAT UBL 2.1. | `10:30:00` |
| *(Definido por moneda de transacción)* | `codigo_moneda` | `/Invoice/cbc:DocumentCurrencyCode` | **Catálogo 02 SUNAT**: Códigos de Moneda (`PEN` = Soles, `USD` = Dólares Americanos). | `PEN` |
| *(RUC del emisor ABC Software Corp)* | `vendedor.ruc` | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID` | **Catálogo 06 SUNAT**: Tipo de Documento de Identidad (`6` = RUC, 11 dígitos, inicia con 10 o 20). | `20556677889` |
| *(Razón Social de ABC Software Corp)* | `vendedor.razon_social` | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | Nombre comercial o denominación legal inscrita en el RUC ante SUNAT. | `ABC SOFTWARE CORP S.A.C.` |
| *(RUC del Cliente Mayorista/Minorista)* | `comprador.ruc` | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID` | **Catálogo 06 SUNAT**: RUC (`6`) para facturas; DNI (`1`) solo para boletas. | `20123456789` |
| *(Razón Social del Cliente)* | `comprador.razon_social` | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | Razón social del adquiriente registrada en el padrón RUC. | `DISTRIBUIDORA DE ABARROTES EL SOL S.A.C.` |
| `producto` (descripción comercial) | `items[].descripcion` | `/Invoice/cac:InvoiceLine/cac:Item/cbc:Description` | Glosa o descripción detallada del bien enajenado. | `Saco de Arroz Extra 50kg` |
| `producto` (código de catálogo interno) | `items[].codigo_producto` | `/Invoice/cac:InvoiceLine/cac:Item/cac:SellersItemIdentification/cbc:ID` | Identificador interno único del producto en el catálogo de ABC Software Corp. | `AB-ARR-001` |
| `salida` (unidades físicas despachadas) | `items[].cantidad` | `/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity` | Unidad de medida normalizada según **Catálogo 03 SUNAT** (`NIU` = Unidad, `KGM` = Kilogramo). | `10.00` |
| *(Precio de venta pactado / 1.18)* | `items[].valor_unitario` | `/Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount` | Valor venta unitario sin tributos. | `100.00` |
| *(Tipo de afectación tributaria)* | `items[].codigo_afectacion_igv` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID` | **Catálogo 07 SUNAT**: Códigos de Afectación al IGV (`10` = Gravado - Operación Onerosa, `20` = Exonerado). | `10` |
| *(Sistema de ISC en licores/gaseosas)* | `items[].codigo_sistema_isc` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TierRange` | **Catálogo 08 SUNAT**: Códigos de Sistema de Cálculo del ISC (`01` = Al valor, `02` = Monto fijo, `03` = Precio de venta al público). | `01` |
| *(Monto de ISC calculado por ítem)* | `items[].isc_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (Scheme `2000`) | Impuesto Selectivo al Consumo aplicado a la base imponible según tasa SUNAT. | `15.00` |
| *(Monto de IGV calculado por ítem)* | `items[].igv_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (Scheme `1000`) | 18% sobre el valor venta unitario acumulado. | `180.00` |
| *(Impuesto a las bolsas plásticas)* | `items[].icbper_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (Scheme `7152`) | Ley N° 30884: S/ 0.50 por bolsa plástica entregada al cliente. | `0.50` |
| *(Suma de bases imponibles gravadas)* | `totales.total_gravadas` | `/Invoice/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` | Sumatoria neta de bienes gravados con IGV. | `1000.00` |
| *(Suma total del IGV)* | `totales.total_igv` | `/Invoice/cac:TaxTotal/cbc:TaxAmount` (Scheme `1000`) | Total liquidado de IGV de la factura. | `180.00` |
| *(Suma total de ISC)* | `totales.total_isc` | `/Invoice/cac:TaxTotal/cbc:TaxAmount` (Scheme `2000`) | Total liquidado de ISC (Catálogo 08) de la factura. | `15.00` |
| *(Suma total de ICBPER)* | `totales.total_icbper` | `/Invoice/cac:TaxTotal/cbc:TaxAmount` (Scheme `7152`) | Total liquidado de ICBPER de la factura. | `0.50` |
| *(Total a pagar por el cliente)* | `totales.importe_total` | `/Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount` | Importe total de la venta: Gravadas + IGV + ISC + ICBPER. | `1195.50` |
| `ingreso` (reposición de mercadería) | `tipo_movimiento = INGRESO_ALMACEN` | *(Kardex Valorizado RS 234-2006)* | Entradas de inventario: genera asiento de Kardex formal sin comprobante UBL de venta. | `50` (sacos) |

---

## 3. Historias de Usuario BDD (Gherkin)

### HU-01: Emisión de Factura Electrónica UBL 2.1 para Distribución de Abarrotes
**Como** Facturador de ABC Software Corp  
**Quiero** generar un comprobante electrónico con validación UBL 2.1 y Catálogo 08 de ISC  
**Para** cumplir con la RS N° 097-2012/SUNAT y remitir el XML al OSE/SUNAT sin rechazos.

```gherkin
Característica: Emisión de Factura Electrónica UBL 2.1
  Como facturador de ABC Software Corp
  Quiero enviar un payload de comprobante estructurado
  Para obtener la factura aprobada con firma digital, Hash CPE y XML conforme a UBL-Invoice-2.1.xsd

  Escenario: Emisión exitosa de factura de abarrotes con IGV
    Dado que el emisor tiene RUC "20556677889" y razón social "ABC SOFTWARE CORP S.A.C."
    Y el comprador mayorista tiene RUC "20123456789"
    Y el `serie_numero` (mapeado a cbc:ID) es "F001-000001"
    Y la factura incluye el ítem "Saco de Arroz Extra 50kg" con cantidad 2, valor unitario 100.00 e IGV 36.00
    Cuando se invoca el servicio POST "/api/v1/facturas"
    Entonces la respuesta HTTP debe ser 201 Created
    Y el campo "serie_numero" en la respuesta debe ser "F001-000001"
    Y el campo "estado_sunat" debe ser "ACEPTADO"
    Y el campo "hash_cpe" debe contener un hash SHA-256 no vacío
    Y el campo "xml_ubl_generado" debe incluir "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>"
    Y el campo "xml_ubl_generado" debe incluir "<cbc:ID>F001-000001</cbc:ID>"

  Escenario: Emisión de mercadería con Impuesto Selectivo al Consumo (Catálogo 08 SUNAT)
    Dado que se despacha mercadería sujeta a ISC con sistema "01" (Al valor)
    Y el campo "codigo_sistema_isc" es "01"
    Y el monto "isc_item" es 15.00
    Cuando se envía la solicitud al endpoint POST "/api/v1/facturas"
    Entonces el comprobante debe ser aceptado con código HTTP 201
    Y el XML UBL generado debe incluir el nodo TaxScheme con ID "2000" y TaxTypeCode "ISC"

  Escenario: Rechazo de factura por código inválido de Catálogo 08 de ISC
    Dado que el operador envía un ítem con "codigo_sistema_isc" igual a "99" (código inexistente en Catálogo 08)
    Cuando se envía la solicitud al endpoint POST "/api/v1/facturas"
    Entonces el sistema responde con código HTTP 400 Bad Request
    Y el código de error devuelto es "ERR-SUNAT-CAT08"
    Y el mensaje detalla la no conformidad con el Catálogo 08 de SUNAT

  Escenario: Rechazo de factura por RUC de cliente no válido
    Dado que el cliente tiene un RUC de 6 dígitos "123456"
    Cuando se envía la solicitud al endpoint POST "/api/v1/facturas"
    Entonces el sistema responde con código HTTP 400 Bad Request
    Y el código de error devuelto es "ERR-SUNAT-RUC"
```

---

### HU-02: Migración y Trazabilidad de Fichas Informales de Almacén a Comprobantes UBL
**Como** Jefe de Almacén de ABC Software Corp  
**Quiero** procesar las fichas informales históricas (`fecha`, `ingreso`, `salida`, `producto`, `nro_documento`)  
**Para** clasificar los despachos pendientes de facturación e incorporarlos al Kardex formal RS N° 234-2006 con correlativo UBL.

```gherkin
Característica: Migración de Fichas Informales de Almacén
  Como analista de inventarios
  Quiero transformar fichas legadas
  Para asegurar trazabilidad tributaria entre el almacén y la facturación UBL

  Escenario: Migración de vale informal de salida a comprobante formal UBL
    Dado un registro legado con fecha "2026-10-15", salida 5, ingreso 0, producto "Saco de Azúcar Rubia 50kg" y nro_documento "VALE-SALIDA-0042"
    Cuando se envía al endpoint POST "/api/v1/migracion/fichas-legado"
    Entonces el código de respuesta HTTP es 201 Created
    Y el campo "tipo_movimiento" es "SALIDA_POR_FACTURAR"
    Y el campo "estado_trazabilidad" es "MIGRADO_CON_TRAZABILIDAD"
    Y el campo "serie_ubl_sugerida" genera la serie correlativa de facturación (ejemplo "F001-000002")

  Escenario: Migración de guía interna de reposición (ingreso de almacén)
    Dado un registro legado con fecha "2026-10-16", ingreso 20, salida 0, producto "Saco de Arroz Extra 50kg" y nro_documento "GUIA-INT-0015"
    Cuando se envía al endpoint POST "/api/v1/migracion/fichas-legado"
    Entonces el código de respuesta HTTP es 201 Created
    Y el campo "tipo_movimiento" es "INGRESO_ALMACEN"
    Y el movimiento se asienta en el Kardex formal sin generar deuda tributaria de venta

  Escenario: Rechazo de ficha legado con datos inconsistentes (ingreso 0 y salida 0)
    Dado un registro legado con ingreso 0 y salida 0
    Cuando se envía al endpoint POST "/api/v1/migracion/fichas-legado"
    Entonces el sistema responde con código HTTP 400 Bad Request
    Y el mensaje de error indica que el movimiento de almacén debe tener una cantidad mayor a cero
```

---

## 4. Matriz de Cobertura de Criterios de Aceptación vs. Tests Automatizados

| Criterio de Aceptación / Escenario | Endpoint / Operación | Test Unitario (Fase Roja/Verde) | Test de Aceptación E2E |
| :--- | :--- | :--- | :--- |
| Emisión válida UBL 2.1 con `serie_numero` (`<cbc:ID>`) | `POST /api/v1/facturas` | `tests/unit/test_factura_service.py::test_emitir_factura_exitosa` | `tests/acceptance/test_facturacion_sdd.py::test_emision_factura_valida_201` |
| Validación Catálogo 08 ISC (`01`, `02`, `03`) | `POST /api/v1/facturas` | `tests/unit/test_factura_service.py::test_validar_catalogo08_isc` | `tests/acceptance/test_facturacion_sdd.py::test_emision_factura_catalogo08_isc_invalido_400` |
| Validación RUC 11 dígitos emisor y receptor | `POST /api/v1/facturas` | `tests/unit/test_factura_service.py::test_validar_ruc` | `tests/acceptance/test_facturacion_sdd.py::test_emision_factura_ruc_invalido_400` |
| Consulta trazabilidad de comprobante emitido | `GET /api/v1/facturas/{serie_numero}` | `tests/unit/test_factura_service.py::test_consultar_factura` | `tests/acceptance/test_facturacion_sdd.py::test_consultar_factura_existente_200` |
| Migración de salida informal de almacén | `POST /api/v1/migracion/fichas-legado` | `tests/unit/test_migracion_service.py::test_migrar_salida` | `tests/acceptance/test_facturacion_sdd.py::test_migracion_ficha_legado_salida_201` |
| Migración de ingreso por reposición de stock | `POST /api/v1/migracion/fichas-legado` | `tests/unit/test_migracion_service.py::test_migrar_ingreso` | `tests/acceptance/test_facturacion_sdd.py::test_migracion_ficha_legado_ingreso_201` |
