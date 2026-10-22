# Especificación BDD y TABLA DE MATCH Normativa (SDD)
> Índice: la sección **[TABLA DE MATCH: LEGADO <-> SUNAT PERÚ <-> OASIS UBL-Invoice-2.1.xsd](#tabla-de-match-legado---sunat-perú---oasis-ubl-invoice-21xsd)** está al final de este documento (Sección 2).
## Proyecto: ABC Software Corp - Facturación UBL 2.1 y Migración Legado

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
**Como** Sistema de Facturación Electrónica  
**Quiero** validar el tipo de sistema de cálculo del Impuesto Selectivo al Consumo (ISC)  
**Para** evitar la emisión de facturas inconsistentes con la RS N° 097-2012 y el Catálogo 08.

```gherkin
Característica: Validación del Catálogo 08 de ISC de SUNAT
  Como motor tributario
  Quiero verificar los sistemas de ISC autorizados ("01", "02", "03")
  Para cumplir con la normativa fiscal de productos afectos a ISC

  Escenario: Emisión con ISC Sistema al Valor ("01") válido
    Dado un ítem con código de sistema ISC "01" (Sistema al valor)
    Y un monto de ISC declarado correspondiente a la tasa
    Cuando se envía la factura para emisión
    Entonces el comprobante es aceptado con estado "ACEPTADO"
    Y el total de ISC se refleja en cac:TaxTotal

  Escenario: Rechazo por código de sistema ISC no registrado en Catálogo 08
    Dado un ítem con código de sistema ISC "99" (código inexistente en Catálogo 08)
    Cuando se envía la factura para emisión
    Entonces el código de respuesta HTTP debe ser 400
    Y el error debe indicar incumplimiento del Catálogo 08 de SUNAT
```

---

### HU-03: Migración de Fichas Informales del Software Legado de Almacén
**Como** Administrador de Logística y Almacén  
**Quiero** procesar fichas históricas informales de almacén (`fecha`, `ingreso`, `salida`, `producto`, `nro_documento`)  
**Para** transformarlas en entidades formales trazables listas para emisión fiscal UBL.

```gherkin
Característica: Migración de Fichas Informales de Almacén
  Como administrador del almacén legado
  Quiero transformar registros informales en transacciones formales
  Para obtener trazabilidad completa hacia facturación electrónica UBL 2.1

  Escenario: Migración exitosa de vale de salida hacia comprobante UBL sugerido
    Dado un registro histórico del almacén con "nro_documento": "VALE-SALIDA-0042"
    Y "salida": 5, "ingreso": 0, "producto": "Saco de Azúcar Rubia 50kg"
    Cuando se envía la solicitud POST al endpoint "/api/v1/migracion/fichas-legado"
    Entonces el código de respuesta HTTP debe ser 201
    Y el campo "tipo_movimiento" debe ser "SALIDA_POR_FACTURAR"
    Y el campo "estado_trazabilidad" debe ser "MIGRADO_CON_TRAZABILIDAD"
    Y se debe asignar un identificador de migración "MIG-..." y serie UBL sugerida

  Escenario: Migración de registro de reposición con movimiento de ingreso
    Dado un registro histórico con "ingreso": 20 y "salida": 0
    Cuando se procesa la migración
    Entonces el tipo de movimiento resultante debe ser "INGRESO_ALMACEN"
```

---

### HU-04: Consulta de Comprobante Emitido y Trazabilidad XML/Hash
**Como** Auditor o Cliente Receptor  
**Quiero** consultar un comprobante por su `serie_numero`  
**Para** descargar el XML UBL 2.1 generado y verificar el Hash CPE y estado SUNAT.

```gherkin
Característica: Consulta de Comprobante UBL
  Como receptor del comprobante
  Quiero consultar el comprobante por su serie_numero "F001-000001"
  Para recuperar su constancia y XML

  Escenario: Consulta exitosa de comprobante existente
    Dado que existe una factura emitida con serie_numero "F001-000001"
    Cuando se realiza una petición GET a "/api/v1/facturas/F001-000001"
    Entonces el código de respuesta HTTP es 200
    Y el objeto contiene el "hash_cpe" y "xml_ubl_generado"

  Escenario: Consulta de comprobante inexistente
    Dado que no existe ningún comprobante con serie_numero "F999-999999"
    Cuando se realiza una petición GET a "/api/v1/facturas/F999-999999"
    Entonces el código de respuesta HTTP es 404
```

---

## TABLA DE MATCH: LEGADO <-> SUNAT PERÚ <-> OASIS UBL-Invoice-2.1.xsd

Cruce explícito entre el **Sistema Legado** de almacén de ABC Software Corp, el **Modelo SUNAT Perú** (DTOs del contrato `specs/contracts/ubl-invoice-api.yaml`, RS N° 097-2012 y Catálogos SUNAT) y el estándar **OASIS `UBL-Invoice-2.1.xsd`**.

| Campo Sistema Legado | Nombre en Modelo SUNAT Perú (DTO) | Nodo / XPath en `UBL-Invoice-2.1.xsd` (OASIS) | Catálogo / Regla SUNAT (RS 097-2012) | Ejemplo Real |
| :--- | :--- | :--- | :--- | :--- |
| `nro_documento` | **`serie_numero`** | `/Invoice/cbc:ID` (`<cbc:ID>`) | Serie F + 3 dígitos, guion y correlativo de hasta 8 dígitos (`^F\d{3}-\d{1,8}$`) | `F001-000001` |
| `nro_documento` (vale/guía interna, trazabilidad) | `nro_documento_legado_origen` | `/Invoice/cac:DespatchDocumentReference/cbc:ID` | Referencia documentaria de guía/vale origen (Anexo 1 RS 097-2012) | `VALE-SALIDA-0042` |
| `fecha` | `fecha_emision` | `/Invoice/cbc:IssueDate` (`<cbc:IssueDate>`) | Fecha de emisión formato `YYYY-MM-DD` | `2026-10-22` |
| Tipo de comprobante (no existe en legado; fijo "Factura") | `tipo_documento_codigo` | `/Invoice/cbc:InvoiceTypeCode` (`<cbc:InvoiceTypeCode>`) | **Catálogo 01**: `01` = Factura | `01` |
| Moneda (no existe en legado; por defecto soles) | `codigo_moneda` | `/Invoice/cbc:DocumentCurrencyCode` | **Catálogo 02**: `PEN`, `USD` | `PEN` |
| Vendedor / Emisor (dato maestro ABC Software Corp) | `vendedor.ruc` / `vendedor.razon_social` | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='6']` y `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | **Catálogo 06**: `6` = RUC (11 dígitos, prefijo 10 o 20) | `20556677889` / `ABC SOFTWARE CORP S.A.C.` |
| Comprador / Cliente (no existe en legado) | `comprador.ruc` / `comprador.razon_social` | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='6']` y `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | **Catálogo 06**: `6` = RUC (11 dígitos, prefijo 10 o 20) | `20123456789` / `DISTRIBUIDORA NORTE S.A.C.` |
| `producto` | `items[].descripcion` | `/Invoice/cac:InvoiceLine/cac:Item/cbc:Description` | Descripción del bien transferido (Anexo 1 RS 097-2012) | `Saco de Arroz Extra 50kg` |
| `salida` (o `ingreso` en reposición) | `items[].cantidad` | `/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity` | Cantidad de unidades > 0 | `2` |
| (Derivado del costo; no existe en legado) | `items[].valor_unitario` | `/Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount` | Valor unitario sin IGV en operaciones gravadas | `100.00` |
| Afectación IGV (no existe en legado) | `items[].codigo_afectacion_igv` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReasonCode` | **Catálogo 07**: `10` = Gravado - Operación Onerosa (IGV 18%) | `10` |
| Sistema de Cálculo ISC (no existe en legado) | `items[].codigo_sistema_isc` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TierRange` | **Catálogo 08 SUNAT**: `01` Sistema al valor, `02` Aplicación del Monto Fijo, `03` Sistema de Precios de Venta al Público | `01` |
| (Calculado) | `items[].isc_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (esquema ISC `2000`) | Monto de ISC según Catálogo 08 | `0.00` |
| (Calculado) | `items[].igv_item` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (esquema IGV `1000`) | IGV 18% sobre base gravada | `36.00` |
| (Calculado) | `totales.total_igv` | `/Invoice/cac:TaxTotal/cbc:TaxAmount` | Total IGV del comprobante | `36.00` |
| Totales (calculado) | `totales.importe_total` | `/Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount` | Importe total a pagar | `236.00` |
| (Respuesta OSE/SUNAT) | `hash_cpe` | `/Invoice/ext:UBLExtensions/.../ds:DigestValue` | Resumen SHA-256 de la firma digital | `sha256-4a8b9c1d2e3f` |
| (Respuesta OSE/SUNAT) | `estado_sunat` / `mensaje_ose` | `ApplicationResponse` (CDR) UBL | Constancia de Recepción ACEPTADO/RECHAZADO | `ACEPTADO` |

