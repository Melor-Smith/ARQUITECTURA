# Matriz de trazabilidad normativa

**Sistema antiguo → SUNAT → OASIS UBL 2.1 (con la cardinalidad del XSD) → contrato API → PLE 14.1 / 12.1 → código de error → prueba**

## Cómo se construye y por qué se puede confiar en ella

- **Fuente única:** [`matriz.yaml`](matriz.yaml). Las tablas del bloque siguiente y el archivo [`matriz.csv`](matriz.csv), que se abre en Excel, se **generan** con `python scripts/matriz.py`. No se editan a mano.
- **Cardinalidad calculada, no copiada.** El script recorre los XSD oficiales de OASIS ([`specs/contracts/ubl-2.1/xsd`](../contracts/ubl-2.1/xsd)) siguiendo cada XPath elemento por elemento. Para los atributos, sigue también la herencia de tipos (por ejemplo, `currencyID` es obligatorio y `unitCode` es opcional).
- **Columna "Perfil SUNAT".** Marca con ⚠ los datos que **SUNAT exige** pero el XSD de OASIS deja **opcionales** en algún punto de la ruta. Ahí el XSD no alcanza, y por eso la regla vive en el dominio y en las pruebas de generación.
- **La propia matriz está probada** ([`tests/integration/test_matriz.py`](../../tests/integration/test_matriz.py)):
  1. **Cada XPath se evalúa contra XML reales** generados por el sistema (factura, boleta, crédito, exportación, vale legado, notas de crédito y débito): si un XPath no encuentra nada, la prueba falla.
  2. **Cada prueba citada existe** en `tests/`.
  3. **Cada código de error citado existe** en `src/`.
  4. **El bloque generado está al día** con el YAML.

Fuentes: RS 097-2012/SUNAT y anexos (catálogos), RS 193-2020/SUNAT (forma de pago), RS 286-2009/SUNAT (PLE), RS 234-2006/SUNAT (registros de inventario), Ley 30884 (ICBPER), TUO de la Ley del IGV e ISC, y OASIS UBL 2.1.

**Leyenda.** SUNAT: **O** = obligatorio y **C** = condicional (depende de la operación). Un "—" en XPath indica un dato que no viaja en el XML: es del libro electrónico o del inventario.

## Matriz

<!-- matriz:inicio (generado por scripts/matriz.py) -->

### 1. Identificación del comprobante

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T01 | Versión UBL | OASIS UBL 2.1 | O | `/Invoice/cbc:UBLVersionID` | 0..1 | ⚠ SUNAT exige; XSD opcional | `(constante)` | — | — | — | — | `test_version_ubl_y_personalizacion_sunat` |
| T02 | Versión de la estructura SUNAT | Perfil SUNAT 2.0 | O | `/Invoice/cbc:CustomizationID` | 0..1 | ⚠ SUNAT exige; XSD opcional | `(constante)` | — | — | — | — | `test_version_ubl_y_personalizacion_sunat` |
| T03 | Serie y correlativo | Serie [FB][A-Z0-9]{3}; correlativo 1-99999999 | O | `/Invoice/cbc:ID` | 1..1 |  | `serie (correlativo lo asigna el servidor)` | — | 7, 8 | 12, 13 | `ERR-SUNAT-SERIE` | `test_cbc_id_une_serie_y_correlativo_solo_al_serializar` |
| T04 | Fecha de emisión | Plazo de envío (configurable) | O | `/Invoice/cbc:IssueDate` | 1..1 |  | `fecha_emision` | — | 4 | — | `ERR-SUNAT-FECHA` | `test_fecha_y_hora_de_emision` |
| T05 | Hora de emisión | SEE | C | `/Invoice/cbc:IssueTime` | 0..1 |  | `(servidor)` | — | — | — | — | `test_fecha_y_hora_de_emision` |
| T06 | Tipo de comprobante | Cat. 01 | O | `/Invoice/cbc:InvoiceTypeCode` | 0..1 | ⚠ SUNAT exige; XSD opcional | `tipo_comprobante` | — | 6 | 11 | — | `test_invoice_type_code_catalogo_01_y_tipo_de_operacion_catalogo_51` |
| T07 | Tipo de operación | Cat. 51 | O | `/Invoice/cbc:InvoiceTypeCode/@listID` | atributo opcional | ⚠ SUNAT exige; XSD opcional | `(derivado de las afectaciones)` | — | — | — | — | `test_invoice_type_code_catalogo_01_y_tipo_de_operacion_catalogo_51` |
| T08 | Importe en letras | Cat. 52 (leyenda 1000) | O | `/Invoice/cbc:Note[@languageLocaleID='1000']` | 0..n | ⚠ SUNAT exige; XSD opcional | `monto_en_letras (respuesta)` | — | — | — | — | `test_leyenda_1000_importe_en_letras` |
| T09 | Moneda | Cat. 02 / Tabla 4 | O | `/Invoice/cbc:DocumentCurrencyCode` | 0..1 | ⚠ SUNAT exige; XSD opcional | `moneda` | — | 26 | — | `ERR-SUNAT-CAT02` | `test_moneda_catalogo_02_en_el_documento_y_en_cada_importe` |
| T10 | Moneda de cada importe | Cat. 02 | O | `/Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount/@currencyID` | atributo obligatorio |  | `moneda` | — | — | — | — | `test_moneda_catalogo_02_en_el_documento_y_en_cada_importe` |
| T11 | Tipo de cambio | Formato 14.1 | C | — | — |  | `tipo_cambio` | — | 27 | — | `ERR-SUNAT-COMPROBANTE` | `test_usd_requiere_tipo_de_cambio` |
| T12 | Vale facturado (documento relacionado) | Cat. 12 tipo 99 | C | `/Invoice/cac:AdditionalDocumentReference/cbc:ID` | 1..1 |  | `documentos_legado[]` | `nro_documento` | — | — | `ERR-LEGADO-NO-MIGRADO` | `test_vale_legado_como_documento_relacionado_catalogo_12_tipo_99` |
| T13 | Tipo de documento relacionado | Cat. 12 | C | `/Invoice/cac:AdditionalDocumentReference/cbc:DocumentTypeCode` | 0..1 |  | `(constante 99)` | — | — | — | — | `test_vale_legado_como_documento_relacionado_catalogo_12_tipo_99` |
| T14 | Documento que sustenta el movimiento | Tabla 10 PLE | O | — | — |  | `nro_documento (migración)` | `nro_documento` | — | 11, 12, 13 | — | `test_reconoce_el_documento_real` |
| T15 | Fecha del movimiento de inventario | Formato 12.1 | O | — | — |  | `fecha (migración)` | `fecha` | — | 10 | `ERR-LEGADO-FECHA` | `test_formatos_de_fecha` |

### 2. Emisor y adquiriente

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T20 | RUC del emisor | Cat. 06 + módulo 11 | O | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID` | 1..1 | ⚠ SUNAT exige; XSD opcional | `(configuración del servidor)` | — | (nombre de archivo) | (nombre de archivo) | `ERR-SUNAT-RUC` | `test_emisor_ruc_razon_social_y_establecimiento` |
| T21 | Tipo de documento del emisor | Cat. 06 | O | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID/@schemeID` | atributo opcional | ⚠ SUNAT exige; XSD opcional | `(constante 6)` | — | — | — | — | `test_emisor_ruc_razon_social_y_establecimiento` |
| T22 | Nombre comercial | Perfil SUNAT | C | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name` | 1..1 |  | `(configuración)` | — | — | — | — | `test_emisor_ruc_razon_social_y_establecimiento` |
| T23 | Razón social del emisor | Padrón RUC | O | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | 0..1 | ⚠ SUNAT exige; XSD opcional | `(configuración)` | — | — | — | — | `test_emisor_ruc_razon_social_y_establecimiento` |
| T24 | Establecimiento anexo | Código SUNAT del establecimiento | O | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cbc:AddressTypeCode` | 0..1 | ⚠ SUNAT exige; XSD opcional | `establecimiento (migración)` | — | — | 4 | — | `test_emisor_ruc_razon_social_y_establecimiento` |
| T25 | Ubigeo del emisor | INEI | C | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cbc:ID` | 0..1 |  | `(configuración)` | — | — | — | — | `test_emisor_ruc_razon_social_y_establecimiento` |
| T26 | Tipo de documento del cliente | Cat. 06 / Tabla 2 | O | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID/@schemeID` | atributo opcional | ⚠ SUNAT exige; XSD opcional | `cliente.tipo_documento` | — | 10 | — | `ERR-SUNAT-CAT06` | `test_cliente_con_dni_en_boleta` |
| T27 | Número de documento del cliente | Cat. 06 (RUC: módulo 11; DNI: 8 dígitos) | O | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID` | 1..1 | ⚠ SUNAT exige; XSD opcional | `cliente.numero_documento` | — | 11 | — | `ERR-SUNAT-RUC` | `test_cliente_con_ruc` |
| T28 | Nombre o razón social del cliente | Padrón RUC / RENIEC | O | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | 0..1 | ⚠ SUNAT exige; XSD opcional | `cliente.nombre` | — | 12 | — | — | `test_nombre_con_ampersand_se_escapa_y_se_recupera_intacto` |
| T29 | Referencia UBL a la firma | Perfil SUNAT | O | `/Invoice/cac:Signature/cbc:ID` | 1..1 | ⚠ SUNAT exige; XSD opcional | `(servidor)` | — | — | — | — | `test_el_xml_se_genera_sin_firma_la_agrega_el_adaptador_de_firma` |

### 3. Líneas de detalle

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T30 | Número de línea | Perfil SUNAT | O | `/Invoice/cac:InvoiceLine/cbc:ID` | 1..1 |  | `(orden de lineas[])` | — | — | — | — | `test_una_invoice_line_por_cada_linea_del_dominio_numerada_desde_1` |
| T31 | Cantidad | Perfil SUNAT | O | `/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity` | 0..1 | ⚠ SUNAT exige; XSD opcional | `lineas[].cantidad` | `ingreso / salida × factor` | — | 17 / 18 (salida en negativo) | — | `test_cantidad_valor_de_venta_y_valor_unitario` |
| T32 | Unidad de medida | Cat. 03 (UN/ECE Rec. 20); el 12.1 usa el mismo código | O | `/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity/@unitCode` | atributo opcional | ⚠ SUNAT exige; XSD opcional | `lineas[].unidad_medida` | — | — | 16 (tabla 6) | `ERR-SUNAT-CAT03` | `test_unidad_de_medida_catalogo_03_por_linea` |
| T33 | Valor de venta de la línea | Perfil SUNAT | O | `/Invoice/cac:InvoiceLine/cbc:LineExtensionAmount` | 1..1 |  | `lineas[].valor_venta (respuesta)` | — | — | — | — | `test_cantidad_valor_de_venta_y_valor_unitario` |
| T34 | Precio unitario con impuestos | Cat. 16 (tipo 01) | O | `/Invoice/cac:InvoiceLine/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount` | 1..1 | ⚠ SUNAT exige; XSD opcional | `lineas[].precio_unitario (respuesta)` | — | — | — | — | `test_precio_unitario_con_impuestos_catalogo_16` |
| T35 | Valor unitario sin impuestos | Perfil SUNAT | O | `/Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount` | 1..1 | ⚠ SUNAT exige; XSD opcional | `lineas[].valor_unitario` | — | — | — | — | `test_cantidad_valor_de_venta_y_valor_unitario` |
| T36 | Descripción del bien | Perfil SUNAT | O | `/Invoice/cac:InvoiceLine/cac:Item/cbc:Description` | 0..n | ⚠ SUNAT exige; XSD opcional | `lineas[].descripcion` | `producto` | — | 15 | — | `test_descripcion_y_codigo_del_producto` |
| T37 | Código del producto | Tabla 13 (catálogo propio) | C | `/Invoice/cac:InvoiceLine/cac:Item/cac:SellersItemIdentification/cbc:ID` | 1..1 |  | `lineas[].codigo_producto` | `producto (homologado)` | — | 5, 7 | `ERR-PRODUCTO-NO-EXISTE` | `test_descripcion_y_codigo_del_producto` |
| T38 | Cantidad acreditada | Nota de crédito | O | `/CreditNote/cac:CreditNoteLine/cbc:CreditedQuantity` | 0..1 | ⚠ SUNAT exige; XSD opcional | `lineas[].cantidad` | — | — | — | — | `test_notas_usan_credited_quantity_y_debited_quantity` |
| T39 | Cantidad debitada | Nota de débito | O | `/DebitNote/cac:DebitNoteLine/cbc:DebitedQuantity` | 0..1 | ⚠ SUNAT exige; XSD opcional | `lineas[].cantidad` | — | — | — | — | `test_notas_usan_credited_quantity_y_debited_quantity` |

### 4. Tributos (calculados por el servidor)

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T40 | Afectación del IGV | Cat. 07 | O | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReasonCode` | 0..1 | ⚠ SUNAT exige; XSD opcional | `lineas[].afectacion_igv` | — | 13, 14, 18, 19 | — | `ERR-SUNAT-CAT07` | `test_igv_gravado_categoria_s_18_por_ciento_y_afectacion_10` |
| T41 | Código del tributo | Cat. 05 | O | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID` | 0..1 | ⚠ SUNAT exige; XSD opcional | `(derivado)` | — | — | — | — | `test_igv_gravado_categoria_s_18_por_ciento_y_afectacion_10` |
| T42 | Categoría del tributo | UN/ECE 5305 (S | O | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:ID` | 0..1 | ⚠ SUNAT exige; XSD opcional | `(derivado)` | — | — | — | — | `test_exonerado_e_inafecto` |
| T43 | Sistema de cálculo del ISC | Cat. 08 | C | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='2000']/cac:TaxCategory/cbc:TierRange` | 0..1 |  | `lineas[].isc.sistema` | — | — | — | `ERR-SUNAT-CAT08` | `test_isc_catalogo_08_en_tier_range` |
| T44 | Tasa del ISC (sistemas 01 y 03) | Cat. 08 | C | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='2000']/cac:TaxCategory/cbc:Percent` | 0..1 |  | `lineas[].isc.tasa` | — | — | — | — | `test_isc_al_valor_lleva_porcentaje_y_monto_fijo_lleva_importe_por_unidad` |
| T45 | Monto fijo del ISC (sistema 02) | Cat. 08 | C | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='2000']/cac:TaxCategory/cbc:PerUnitAmount` | 0..1 |  | `lineas[].isc.monto_fijo` | — | — | — | — | `test_isc_al_valor_lleva_porcentaje_y_monto_fijo_lleva_importe_por_unidad` |
| T46 | ISC de la línea | TUO Ley IGV-ISC art. 56 | C | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='2000']/cbc:TaxAmount` | 1..1 |  | `lineas[].isc.monto (respuesta)` | — | 20 (suma) | — | — | `test_isc_catalogo_08_en_tier_range` |
| T47 | IGV de la línea (18 % sobre valor + ISC) | TUO Ley IGV | O | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='1000']/cbc:TaxAmount` | 1..1 | ⚠ SUNAT exige; XSD opcional | `lineas[].igv (respuesta)` | — | 16 (suma) | — | — | `test_el_igv_se_calcula_sobre_valor_de_venta_mas_isc` |
| T48 | ICBPER de la línea | Ley 30884 | C | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='7152']/cbc:TaxAmount` | 1..1 |  | `lineas[].aplica_icbper` | — | 23 (suma) | — | `ERR-SUNAT-CAT03` | `test_icbper_por_bolsa` |
| T49 | Tasa del ICBPER por bolsa | Ley 30884 | C | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='7152']/cac:TaxCategory/cbc:PerUnitAmount` | 0..1 |  | `(por año de emisión)` | — | — | — | — | `test_icbper_por_bolsa` |
| T50 | Total de tributos | Perfil SUNAT | O | `/Invoice/cac:TaxTotal/cbc:TaxAmount` | 1..1 | ⚠ SUNAT exige; XSD opcional | `totales.total_impuestos` | — | — | — | — | `test_tax_total_del_documento_suma_el_de_las_lineas` |
| T51 | Base de operaciones gravadas | Cat. 05 (1000) | C | `/Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='1000']/cbc:TaxableAmount` | 0..1 |  | `totales.gravadas` | — | 14 (sin ISC) | — | — | `test_subtotales_del_documento_por_tributo` |
| T52 | Total del IGV | Cat. 05 (1000) | C | `/Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='1000']/cbc:TaxAmount` | 1..1 |  | `totales.igv` | — | 16 | — | — | `test_subtotales_del_documento_por_tributo` |
| T53 | Total exonerado | Cat. 05 (9997) | C | `/Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='9997']/cbc:TaxableAmount` | 0..1 |  | `totales.exoneradas` | — | 18 | — | — | `test_subtotales_del_documento_por_tributo` |
| T54 | Total inafecto | Cat. 05 (9998) | C | `/Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='9998']/cbc:TaxableAmount` | 0..1 |  | `totales.inafectas` | — | 19 | — | — | `test_subtotales_del_documento_por_tributo` |
| T55 | Valor de exportación | Cat. 05 (9995) | C | `/Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='9995']/cbc:TaxableAmount` | 0..1 |  | `totales.exportacion` | — | 13 | — | — | `test_exportacion_9995_categoria_g` |
| T56 | Total del ISC | Cat. 05 (2000) | C | `/Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='2000']/cbc:TaxAmount` | 1..1 |  | `totales.isc` | — | 20 | — | — | `test_subtotales_del_documento_por_tributo` |
| T57 | Total del ICBPER | Cat. 05 (7152) | C | `/Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='7152']/cbc:TaxAmount` | 1..1 |  | `totales.icbper` | — | 23 | — | — | `test_subtotales_del_documento_por_tributo` |

### 5. Totales y forma de pago

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T60 | Valor de venta total | Perfil SUNAT | O | `/Invoice/cac:LegalMonetaryTotal/cbc:LineExtensionAmount` | 0..1 | ⚠ SUNAT exige; XSD opcional | `totales.valor_venta` | — | — | — | — | `test_totales_monetarios` |
| T61 | Total con impuestos | Perfil SUNAT | O | `/Invoice/cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount` | 0..1 | ⚠ SUNAT exige; XSD opcional | `totales.importe_total` | — | — | — | — | `test_totales_monetarios` |
| T62 | Importe total a pagar | Perfil SUNAT | O | `/Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount` | 1..1 |  | `totales.importe_total` | — | 25 | — | — | `test_importe_total_es_valor_de_venta_mas_tributos` |
| T63 | Importe total de la nota de débito | Nota de débito | O | `/DebitNote/cac:RequestedMonetaryTotal/cbc:PayableAmount` | 1..1 |  | `totales.importe_total` | — | 25 | — | — | `test_nota_de_debito_usa_requested_monetary_total` |
| T64 | Forma de pago (Contado / Crédito) | RS 193-2020 | O | `/Invoice/cac:PaymentTerms[cbc:ID='FormaPago']/cbc:PaymentMeansID` | 0..n | ⚠ SUNAT exige; XSD opcional | `forma_pago.tipo` | — | — | — | `ERR-SUNAT-FORMA-PAGO` | `test_forma_de_pago_contado` |
| T65 | Monto neto pendiente de pago | RS 193-2020 | C | `/Invoice/cac:PaymentTerms[cbc:PaymentMeansID='Credito']/cbc:Amount` | 0..1 |  | `(suma de cuotas)` | — | — | — | `ERR-SUNAT-FORMA-PAGO` | `test_forma_de_pago_credito_con_monto_pendiente_y_cuotas` |
| T66 | Cuotas (monto y vencimiento) | RS 193-2020 | C | `/Invoice/cac:PaymentTerms[starts-with(cbc:PaymentMeansID,'Cuota')]/cbc:PaymentDueDate` | 0..1 |  | `forma_pago.cuotas[]` | — | 5 (última cuota, si vence hasta el mes siguiente) | — | `ERR-SUNAT-FORMA-PAGO` | `test_forma_de_pago_credito_con_monto_pendiente_y_cuotas` |

### 6. Notas de crédito y débito

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T70 | Comprobante que se modifica | Nota de crédito / débito | O | `/CreditNote/cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` | 1..1 | ⚠ SUNAT exige; XSD opcional | `referencia.serie_numero` | — | 30, 31 | — | `ERR-REFERENCIA-NO-EXISTE` | `test_nota_de_credito_referencia_y_motivo_catalogo_09` |
| T71 | Tipo del comprobante modificado | Cat. 01 | O | `/CreditNote/cac:BillingReference/cac:InvoiceDocumentReference/cbc:DocumentTypeCode` | 0..1 | ⚠ SUNAT exige; XSD opcional | `referencia.tipo_comprobante` | — | 29 | — | — | `test_nota_de_credito_referencia_y_motivo_catalogo_09` |
| T72 | Motivo de la nota de crédito | Cat. 09 | O | `/CreditNote/cac:DiscrepancyResponse/cbc:ResponseCode` | 0..1 | ⚠ SUNAT exige; XSD opcional | `motivo` | — | — | — | `ERR-SUNAT-MOTIVO-NOTA` | `test_nota_de_credito_referencia_y_motivo_catalogo_09` |
| T73 | Sustento | Nota de crédito / débito | O | `/CreditNote/cac:DiscrepancyResponse/cbc:Description` | 0..n | ⚠ SUNAT exige; XSD opcional | `sustento` | — | — | — | — | `test_nota_de_credito_referencia_y_motivo_catalogo_09` |
| T74 | Motivo de la nota de débito | Cat. 10 | O | `/DebitNote/cac:DiscrepancyResponse/cbc:ResponseCode` | 0..1 | ⚠ SUNAT exige; XSD opcional | `motivo` | — | — | — | `ERR-SUNAT-MOTIVO-NOTA` | `test_nota_de_debito_motivo_catalogo_10` |

### 7. Firma digital

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T80 | Firma XMLDSig | SEE (firma digital) | O | `/Invoice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/ds:Signature` | 1..1 | ⚠ SUNAT exige; XSD opcional | `(servidor)` | — | — | — | — | `test_firma_xmldsig_en_ubl_extensions_y_hash_cpe_es_el_digest_value` |
| T81 | Hash de la representación impresa | SEE | O | `/Invoice/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/ds:Signature/ds:SignedInfo/ds:Reference/ds:DigestValue` | 1..1 | ⚠ SUNAT exige; XSD opcional | `hash_cpe (respuesta)` | — | — | — | — | `test_hash_cpe_es_el_digest_value_del_xml_firmado` |

### 8. Inventario permanente (formato 12.1, sin XML)

| ID | Dato | Norma / catálogo | SUNAT | XPath UBL 2.1 | Card. XSD | Perfil SUNAT | Contrato (JSON) | Sistema antiguo | 14.1 | 12.1 | Error | Prueba |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T90 | Tipo de existencia | Tabla 5 PLE | O | — | — |  | `(dato maestro del producto)` | `producto (homologado)` | — | 6 | — | `test_kardex_con_saldo_final_y_equivalencia_de_unidades` |
| T91 | Tipo de operación | Tabla 12 PLE | O | — | — |  | `tipo_operacion (migración)` | `ingreso / salida` | — | 14 (99 si el documento es interno) | `ERR-KARDEX-DOCUMENTO-OPERACION` | `test_tipo_de_operacion_incompatible` |
| T92 | Unidad de medida del libro | Campo 16 del 12.1: UN/ECE (validado con PLE 5.2.0.7) | O | — | — |  | `(derivado)` | — | — | 16 | — | `test_unidad_con_codigo_numerico_de_la_tabla_6_anterior_se_rechaza` |
| T93 | Saldo en unidades físicas | RS 234-2006 | O | — | — |  | `saldo_final (Kardex)` | — | — | (formato impreso) | `ERR-KARDEX-SALDO-INSUFICIENTE` | `test_no_permite_saldo_negativo` |
| T94 | Estado de la anotación | RS 286-2009 | O | — | — |  | `(servidor)` | — | 35 | 19 | — | `test_txt_del_ple` |

*72 filas; 64 con XPath verificado contra XML generados; 36 brechas de perfil (dato que SUNAT exige y el XSD de OASIS deja opcional).*

<!-- matriz:fin -->

## Tabla de equivalencias: Catálogo 03 (UNECE) → Tabla 6 (PLE)

El XML usa UNECE; los libros 12.1 y 13.1 usan la tabla 6. La equivalencia está en `UnidadMedida.unidad_ple` ([`catalogos.py`](../../src/domain/catalogos.py)).

| Catálogo 03 (UNECE) | Descripción | Tabla 6 PLE | Descripción |
|---|---|---|---|
| KGM | Kilogramo | 01 | Kilogramos |
| LBR | Libra | 02 | Libras |
| TNE | Tonelada métrica | 04 | Toneladas métricas |
| GRM | Gramo | 06 | Gramos |
| NIU | Unidad (bienes) | 07 | Unidades |
| LTR | Litro | 08 | Litros |
| GLL | Galón | 09 | Galones |
| BLL | Barril | 10 | Barriles |
| CA | Lata | 11 | Latas |
| BX | Caja | 12 | Cajas |
| MIL | Millar | 13 | Millares |
| MTQ | Metro cúbico | 14 | Metros cúbicos |
| MTR | Metro | 15 | Metros |
| ZZ, BG, BO, PK, SA, DZN, MLT | Servicio, bolsa, botella, paquete, saco, docena, mililitro | 99 | Otros |

## Homologación: glosa del sistema antiguo → producto

Es un dato maestro ([`semillas.py`](../../src/adapters/outbound/persistencia/semillas.py)). La comparación ignora mayúsculas, tildes y espacios repetidos. Una glosa sin homologar se rechaza con 422 `ERR-LEGADO-NO-HOMOLOGADO` o, dentro de un lote, queda OBSERVADA, salvo que la ficha traiga `codigo_producto` y `factor_conversion`.

| Glosa en el sistema antiguo | Producto | Unidad de inventario | Factor |
|---|---|---|---|
| Saco de Arroz Extra 50kg | AB-ARR-001 | KGM | 50 |
| Saco de Azúcar Rubia 50kg | AB-AZU-001 | KGM | 50 |
| Caja Aceite Vegetal 12x1L | AB-ACE-001 | NIU | 12 |

## Clasificación del `nro_documento` del sistema antiguo → Tabla 10

El campo `nro_documento` no siempre era un vale: el almacén anotaba ahí facturas y boletas físicas, guías y textos libres. `clasificar_documento_legado` ([`inventario.py`](../../src/domain/inventario.py)) reconoce qué documento es. **Nunca** lo convierte en un número de comprobante electrónico nuevo.

| Regla (en orden) | Ejemplos | Tabla 10 | Serie / número | ¿Observación? | Efecto en una salida por venta |
|---|---|---|---|---|---|
| `SIN_DOCUMENTO` | `s/n`, `-`, vacío | 00 | `SN` / AAAAMMDD | Sí | Pendiente de facturar |
| `DOCUMENTO_INTERNO` (prefijos VALE, GUIA-INT, NI, PEDIDO…) | `VALE-SALIDA-0042`, `GUIA-INT-0015` | 00 | `VALE-SALIDA` / `0042` | No | Pendiente de facturar |
| `COMPROBANTE_ELECTRONICO` | `F001-00004587`, `B001-0000231` | 01 / 03 | `B001` / `231` | No | **Ya facturada** (no se vuelve a facturar) |
| `FACTURA_FISICA` | `FACT 001-4587` | 01 | `0001` / `4587` | No | **Ya facturada** |
| `BOLETA_FISICA` | `BOL. 2-15` | 03 | `0002` / `15` | No | **Ya facturada** |
| `GUIA_REMISION` | `GUIA 0002-781`, `GR EG01-55` | 09 | `0002` / `781` | No | Pendiente de facturar (la guía no es comprobante de pago) |
| `NO_RECONOCIDO` | `xyz` | 00 | texto original | Sí | Pendiente de facturar |

Pruebas: `tests/unit/test_inventario_y_libros.py::TestClasificacionDocumentoLegado` y `TestLoteDeMigracion`.

## Correcciones respecto de la versión calificada

| Antes (incorrecto) | Ahora |
|---|---|
| Catálogo 07 → `cac:TaxScheme/cbc:ID` | Catálogo 07 → `cac:TaxCategory/cbc:TaxExemptionReasonCode` (T40); `TaxScheme/cbc:ID` lleva el Catálogo 05 (T41) |
| `nro_documento` → `/Invoice/cbc:ID` | `nro_documento` → documento de soporte del 12.1, clasificado según la tabla 10 (T14), y `cac:AdditionalDocumentReference` del Catálogo 12, tipo 99, cuando se factura (T12) |
| Vale → `DespatchDocumentReference` tipo 09 | Un vale es tipo 00; solo una guía de remisión real es tipo 09 |
| "Kardex valorizado RS 234-2006" | 12.1 = unidades físicas (implementado); 13.1 = valorizado (fuera de alcance) |
| Unidad sin campo en el DTO | `lineas[].unidad_medida` → `@unitCode` (T32), con equivalencia a la tabla 6 |
| Sin 14.1 ni 12.1, sin forma de pago | Columnas 14.1 y 12.1 en toda la matriz, forma de pago RS 193-2020 (T64-T66) y [`specs/ple/`](../ple) |
| Cardinalidades y obligatoriedad escritas a mano | Calculadas desde los XSD y verificadas contra XML generados |
