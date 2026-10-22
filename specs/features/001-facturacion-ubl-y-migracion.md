# Especificación BDD y Tabla de Match Normativa (SDD)
## Proyecto: ABC Software Corp - Facturación Electrónica UBL 2.1 y Migración Legado
### Normativa: SUNAT RS N° 097-2012, RS N° 234-2006 y Estándar OASIS UBL-Invoice-2.1.xsd

---

## 1. Historias de Usuario y Criterios de Aceptación (Gherkin BDD)

### HU-01: Emisión de Factura Electrónica UBL 2.1 (Tipo Nubefact)
**Como** Analista Contable de ABC Software Corp  
**Quiero** emitir comprobantes de pago electrónicos con validación normativa inmediata  
**Para** garantizar la validez legal ante SUNAT/OSE bajo el estándar OASIS UBL 2.1 y RS N° 097-2012.

```gherkin
Característica: Emisión de Factura Electrónica UBL 2.1
  Como emisor contable
  Quiero enviar un payload validado
  Para obtener un comprobante aceptado con XML UBL y Hash CPE

  Escenario: Emisión exitosa de factura electrónica gravada
    Dado que el emisor tiene RUC "20556677889" y el comprador tiene RUC "20123456789"
    Y el `serie_numero` (mapea a cbc:ID) es "F001-000001"
    Y se incluye el producto "Saco de Arroz Extra 50kg" por valor unitario 100.00 con IGV al 18% (afectación 10)
    Cuando se envía la solicitud al endpoint POST "/api/v1/facturas"
    Entonces el código de respuesta HTTP debe ser 201
    Y el campo "estado_sunat" debe ser "ACEPTADO"
    Y el payload debe contener "hash_cpe" no vacío
    Y el nodo "xml_ubl_generado" debe incluir "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>"
    Y el mensaje OSE debe confirmar la aceptación

  Escenario: Rechazo de factura por RUC de comprador inválido
    Dado que el emisor envía un comprobante con RUC de comprador "123456" (menos de 11 dígitos o formato erróneo)
    Cuando se envía la solicitud al endpoint POST "/api/v1/facturas"
    Entonces el código de respuesta HTTP debe ser 400
    Y el campo "codigo" debe ser "ERR-SUNAT-RUC"
```

---

### HU-02: Validación Estricta del Catálogo 08 de SUNAT (Sistemas de ISC)
**Como** Auditor Tributario  
**Quiero** verificar que todo ítem afecto a ISC cumpla con los tipos de sistema autorizados  
**Para** evitar reparos tributarios y multas de SUNAT.

```gherkin
Característica: Validación del Catálogo 08 SUNAT
  Como auditor tributario
  Quiero validar el sistema de cálculo de ISC
  Para asegurar el cumplimiento de la RS N° 097-2012

  Escenario: Factura con cálculo de ISC según Catálogo 08 válido
    Dado que un ítem tiene "codigo_sistema_isc" con valor "01" (Sistema al valor)
    Cuando se procesa el comprobante
    Entonces la factura debe ser aceptada con estado "ACEPTADO"
    Y el XML UBL debe contener el elemento TaxScheme con ID "2000" y TaxTypeCode "ISC"

  Escenario: Rechazo por código de sistema de ISC inexistente en Catálogo 08
    Dado que un ítem tiene "codigo_sistema_isc" con valor "99" (no listado en Catálogo 08)
    Cuando se procesa el comprobante
    Entonces el sistema debe rechazar la solicitud con HTTP 400
    Y el campo "codigo" debe ser "ERR-SUNAT-CAT08"
```

---

### HU-03: Migración de Fichas Informales de Almacén hacia Entidades Formales UBL
**Como** Jefe de Almacén de ABC Software Corp  
**Quiero** migrar los registros informales del software legado (`fecha`, `ingreso`, `salida`, `producto`, `nro_documento`)  
**Para** vincular los despachos de mercadería con comprobantes electrónicos formalizados ante SUNAT.

```gherkin
Característica: Migración de Fichas de Almacén
  Como jefe de almacén
  Quiero transformar fichas legadas
  Para clasificarlas en ingresos de stock o salidas por facturar con correlativo UBL

  Escenario: Migración de vale de salida hacia comprobante UBL formal
    Dado una ficha informal con:
      | fecha          | 2026-10-15             |
      | ingreso        | 0                      |
      | salida         | 5                      |
      | producto       | Saco de Azúcar Rubia 50kg |
      | nro_documento  | VALE-SALIDA-0042       |
    Cuando se envía la solicitud al endpoint POST "/api/v1/migracion/fichas-legado"
    Entonces el código de respuesta HTTP debe ser 201
    Y el campo "tipo_movimiento" debe ser "SALIDA_POR_FACTURAR"
    Y el campo "estado_trazabilidad" debe ser "MIGRADO_CON_TRAZABILIDAD"
    Y se debe generar una sugerencia de serie UBL correlativa (ejemplo "F001-000002")

  Escenario: Rechazo de ficha informal inconsistente sin unidades
    Dado una ficha con ingreso 0 y salida 0
    Cuando se envía la solicitud al endpoint POST "/api/v1/migracion/fichas-legado"
    Entonces el código de respuesta HTTP debe ser 400
    Y el mensaje debe indicar que la cantidad debe ser mayor a cero
```

---

## 2. TABLA DE MATCH: LEGADO <-> SUNAT PERÚ <-> OASIS UBL-Invoice-2.1.xsd

| Campo Sistema Legado ABC Software Corp | Nombre en Modelo SUNAT Perú | Nodo / XPath exacto en OASIS UBL-Invoice-2.1.xsd | Catálogo / Regla Normativa SUNAT | Ejemplo Real de Negocio |
| :--- | :--- | :--- | :--- | :--- |
| `nro_documento` (salida comercial) | **`serie_numero`** | `/Invoice/cbc:ID` | **Regla Serie-Número SUNAT**: Serie alfanumérica `F` + 3 dígitos (`F001`) y correlativo de hasta 8 dígitos (`000001`). Catálogo 01 (`01` = Factura). | `F001-000001` |
| `nro_documento` (trazabilidad origen) | `nro_documento_legado_origen` | `/Invoice/cac:DespatchDocumentReference/cbc:ID` | **RS N° 097-2012 / RS N° 234-2006**: Trazabilidad entre el despacho físico y la factura electrónica. | `VALE-SALIDA-0042` |
| `fecha` | `fecha_emision` | `/Invoice/cbc:IssueDate` | Formato ISO 8601 `YYYY-MM-DD`. Debe ser consistente con el período tributario de despacho. | `2026-10-22` |
| *(Hora de emisión)* | `hora_emision` | `/Invoice/cbc:IssueTime` | Formato ISO 8601 `hh:mm:ss`. Requerido en SUNAT UBL 2.1. | `10:30:00` |
| *(Definido por transacción)* | `codigo_moneda` | `/Invoice/cbc:DocumentCurrencyCode` | **Catálogo 02 SUNAT**: Códigos de Moneda (`PEN` = Soles, `USD` = Dólares Americanos). | `PEN` |
| *(RUC emisor ABC Software Corp)* | `vendedor.ruc` | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID` | **Catálogo 06 SUNAT**: Tipo de Documento de Identidad (`6` = RUC, 11 dígitos). | `20556677889` |
| *(Razón social emisor)* | `vendedor.razon_social` | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | Nombre comercial o denominación legal inscrita en RUC ante SUNAT. | `ABC SOFTWARE CORP S.A.C.` |
| *(RUC cliente)* | `comprador.ruc` | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID` | **Catálogo 06 SUNAT**: RUC (`6`) para facturas con derecho a crédito fiscal. | `20123456789` |
| *(Razón social cliente)* | `comprador.razon_social` | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | Razón social del adquiriente en el padrón RUC. | `DISTRIBUIDORA DE ABARROTES EL SOL S.A.C.` |
| `producto` (glosa comercial) | `items[].descripcion` | `/Invoice/cac:InvoiceLine/cac:Item/cbc:Description` | Glosa o descripción detallada del bien enajenado. | `Saco de Arroz Extra 50kg` |
| `producto` (código de catálogo) | `items[].codigo_producto` | `/Invoice/cac:InvoiceLine/cac:Item/cac:SellersItemIdentification/cbc:ID` | Código interno único de inventario en ABC Software Corp. | `AB-ARR-001` |
| `salida` (unidades despachadas) | `items[].cantidad` | `/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity` | Unidad de medida normalizada según **Catálogo 03 SUNAT** (`NIU` = Unidad, `KGM` = Kilogramo). | `10.00` |
| *(Precio de venta pactado / 1.18)* | `items[].valor_unitario` | `/Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount` | Valor venta unitario sin tributos. | `100.00` |
| *(Tipo de afectación tributaria)* | `items[].codigo_afectacion_igv` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID` | **Catálogo 07 SUNAT**: Códigos de Afectación al IGV (`10` = Gravado - Operación Onerosa). | `10` |
| *(Sistema de ISC en licores/gaseosas)* | `items[].codigo_sistema_isc` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TierRange` | **Catálogo 08 SUNAT**: Tipos de Sistema de Cálculo del ISC (`01` = Al valor, `02` = Monto fijo, `03` = Precio de venta al público). | `01` |
| *(Monto de ISC liquidado)* | `items[].isc_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (Scheme `2000`) | Impuesto Selectivo al Consumo liquidado según tasa SUNAT. | `15.00` |
| *(Monto de IGV liquidado)* | `items[].igv_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (Scheme `1000`) | 18% sobre el valor venta unitario acumulado. | `180.00` |
| *(Impuesto a bolsas plásticas)* | `items[].icbper_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (Scheme `7152`) | Ley N° 30884: S/ 0.50 por bolsa plástica entregada al cliente. | `0.50` |
| *(Suma de gravadas)* | `totales.total_gravadas` | `/Invoice/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` | Sumatoria neta de bienes gravados con IGV. | `1000.00` |
| *(Suma de IGV)* | `totales.total_igv` | `/Invoice/cac:TaxTotal/cbc:TaxAmount` (Scheme `1000`) | Total liquidado de IGV de la factura. | `180.00` |
| *(Suma de ISC)* | `totales.total_isc` | `/Invoice/cac:TaxTotal/cbc:TaxAmount` (Scheme `2000`) | Total liquidado de ISC (Catálogo 08) de la factura. | `15.00` |
| *(Suma de ICBPER)* | `totales.total_icbper` | `/Invoice/cac:TaxTotal/cbc:TaxAmount` (Scheme `7152`) | Total liquidado de ICBPER de la factura. | `0.50` |
| *(Importe total a pagar)* | `totales.importe_total` | `/Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount` | Total liquidado de la venta (Gravadas + IGV + ISC + ICBPER). | `1195.50` |
| `ingreso` (reposición de stock) | `tipo_movimiento = INGRESO_ALMACEN` | *(Kardex Valorizado RS 234-2006)* | Entradas de inventario: genera asiento de Kardex formal sin comprobante UBL de venta. | `50` (sacos) |

---

## 3. Matriz de Trazabilidad Normativa SUNAT vs UBL 2.1

| Requisito Normativo | Base Legal SUNAT | Estándar OASIS UBL 2.1 | Implementación en Sistema |
| :--- | :--- | :--- | :--- |
| Numeración correlativa | RS N° 097-2012 / Anexo I | `/Invoice/cbc:ID` | Campo `serie_numero` validado con regex `^F\d{3}-\d{1,8}$`. |
| Validación de RUC 11 dígitos | Catálogo 06 SUNAT | `cac:AccountingCustomerParty/.../cbc:ID[@schemeID='6']` | Schema Pydantic `ActorParty` y regex `^(10|20)\d{9}$`. |
| Tipos de Sistema de ISC | Catálogo 08 SUNAT | `cac:TaxCategory/cbc:TierRange` (Scheme 2000) | Validación en `ItemFactura` restringida a valores `01`, `02`, `03`. |
| Trazabilidad de Guía/Vale | RS N° 097-2012 / RS N° 234-2006 | `/Invoice/cac:DespatchDocumentReference/cbc:ID` | Campo `nro_documento_legado_origen` mapeado en el XML UBL. |
| Firma Digital y Hash CPE | RS N° 097-2012 / Anexo I | `/Invoice/ext:UBLExtensions/.../ds:DigestValue` | Servicio `SunatUBLService` con cálculo SHA-256 canónico. |
