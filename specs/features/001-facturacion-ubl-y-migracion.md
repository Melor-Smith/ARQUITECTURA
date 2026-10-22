# Especificación BDD y Matriz de Trazabilidad Normativa (SDD)
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
    Y la serie y correlativo es "F001-000001"
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
**Quiero** consultar un comprobante por su serie y correlativo  
**Para** descargar el XML UBL 2.1 generado y verificar el Hash CPE y estado SUNAT.

```gherkin
Característica: Consulta de Comprobante UBL
  Como receptor del comprobante
  Quiero consultar el comprobante por su ID "F001-000001"
  Para recuperar su constancia y XML

  Escenario: Consulta exitosa de comprobante existente
    Dado que existe una factura emitida con ID "F001-000001"
    Cuando se realiza una petición GET a "/api/v1/facturas/F001-000001"
    Entonces el código de respuesta HTTP es 200
    Y el objeto contiene el "hash_cpe" y "xml_ubl_generado"

  Escenario: Consulta de comprobante inexistente
    Dado que no existe ningún comprobante con ID "F999-999999"
    Cuando se realiza una petición GET a "/api/v1/facturas/F999-999999"
    Entonces el código de respuesta HTTP es 404
```

---

## 2. Matriz de Trazabilidad Normativa (Punto 4 del Examen)
Cruce exacto entre datos del sistema legado, normativa tributaria peruana SUNAT (RS N° 097-2012 y Catálogos SUNAT), estándar internacional OASIS UBL 2.1, contrato OpenAPI y tests automatizados.

| Campo Legado (Ficha Almacén) | Regla / Catálogo SUNAT (RS 097-2012 / Catálogo 8) | Elemento XML OASIS `UBL-Invoice-2.1.xsd` | Schema DTO OpenAPI | Test Automatizado que Valida |
| :--- | :--- | :--- | :--- | :--- |
| `nro_documento` (ej. "VALE-SALIDA-0042") | **Trazabilidad de Referencia Documentaria**: Permite referenciar guías, vales o documentos internos autorizados según Anexo 1 RS 097-2012. | `/Invoice/cac:DespatchDocumentReference/cbc:ID` o `/Invoice/cac:AdditionalDocumentReference/cbc:ID` | `FacturaRequest.nro_documento_legado_origen` y `FichaLegadoRequest.nro_documento` | `test_migracion_ficha_legado_exitosa`, `test_factura_con_referencia_legada` |
| `fecha` (ej. "2026-10-15") | **Fecha de Emisión del Comprobante**: Formato obligatorio `YYYY-MM-DD` (Art. 13 RS 097-2012). | `/Invoice/cbc:IssueDate` | `FacturaRequest.fecha_emision` y `FichaLegadoRequest.fecha` | `test_emision_factura_valida`, `test_formato_fecha_emision` |
| `producto` (ej. "Saco de Azúcar Rubia 50kg") | **Descripción del Bien o Servicio**: Descripción clara y detallada del bien transferido (Catálogo 16 / Anexo 1). | `/Invoice/cac:InvoiceLine/cac:Item/cbc:Description` | `ItemFactura.descripcion` y `FichaLegadoRequest.producto` | `test_emision_factura_valida`, `test_item_descripcion_requerida` |
| `salida` / `ingreso` (cantidades operativas) | **Cantidad de Unidades Físicas**: Debe ser número mayor a cero en líneas de comprobante (Anexo 1 RS 097-2012). | `/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity` | `ItemFactura.cantidad` | `test_emision_factura_valida`, `test_calculo_totales_igv_18` |
| *(Derivado del costo unitario)* | **Valor Unitario por Ítem**: Sin IGV en operaciones gravadas (Regla de cálculo Anexo 1). | `/Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount` | `ItemFactura.valor_unitario` | `test_calculo_totales_igv_18` |
| *(Nuevo requisito fiscal)* | **Catálogo 06 SUNAT**: Tipo de documento del receptor y emisor. RUC obligatorio para facturas (código "6"), 11 dígitos iniciando en 10 o 20. | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeID='6']` y `cac:AccountingCustomerParty/...` | `ActorParty.ruc`, `ActorParty.codigo_tipo_documento` | `test_validacion_ruc_11_digitos_invalido`, `test_validacion_ruc_prefijo` |
| *(Nuevo requisito fiscal)* | **Catálogo 07 SUNAT**: Afectación del IGV (ej. "10" = Gravado - Operación Onerosa, tasa 18%). | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReasonCode` | `ItemFactura.codigo_afectacion_igv`, `ItemFactura.igv_item` | `test_afectacion_igv_catalogo_07` |
| *(Requisito Obligatorio ISC)* | **Catálogo 08 SUNAT**: Códigos de Sistema de ISC: `01` (Al valor), `02` (Monto fijo), `03` (Precio venta público). | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TierRange` | `ItemFactura.codigo_sistema_isc`, `ItemFactura.isc_item` | `test_catalogo_08_isc_valido`, `test_catalogo_08_isc_codigo_invalido` |
| *(Nuevo requisito fiscal)* | **Catálogo 02 SUNAT**: Código internacional de moneda según ISO 4217 (ej. "PEN", "USD"). | `/Invoice/cbc:DocumentCurrencyCode` | `FacturaRequest.codigo_moneda` | `test_moneda_catalogo_02` |
| *(Control Fiscal OSE)* | **Firma Digital y Resumen Hash**: Resumen SHA-256 del comprobante firmado digitalmente por el emisor/OSE. | `/Invoice/cac:Signature` y `/Invoice/ext:UBLExtensions/.../ds:DigestValue` | `FacturaResponse.hash_cpe` | `test_emision_factura_valida`, `test_generacion_hash_cpe` |
| *(Control Legal OSE)* | **Constancia de Recepción (CDR) y Aceptación**: Dictamen del OSE o SUNAT que confiere validez jurídica. | Documento ApplicationResponse (CDR) UBL | `FacturaResponse.estado_sunat`, `FacturaResponse.mensaje_ose` | `test_emision_factura_valida`, `test_consultar_factura_existente` |
