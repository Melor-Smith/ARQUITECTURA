# Modelo de Dominio de Negocio y Reglas Tributarias SUNAT
## Empresa: ABC Software Corp
### Sector: Distribución y Venta de Abarrotes al Por Mayor y Menor
### Normativas Aplicables: RS N° 097-2012, RS N° 234-2006, Ley N° 30884 y Catálogo 08 SUNAT

---

## 1. Entidades del Dominio

### 1.1. FacturaElectrónica (Aggregate Root)
Representa el comprobante de pago con efectos tributarios emitido por ABC Software Corp hacia sus clientes mayoristas o minoristas.
* **Atributos Principales**:
  * `serie_numero`: Identificador unívoco del comprobante (formato SUNAT: `F001-000001`). Mapea a `<cbc:ID>` de UBL 2.1.
  * `fecha_emision`: Fecha de devengo contable y tributario (`YYYY-MM-DD`). Mapea a `<cbc:IssueDate>`.
  * `codigo_moneda`: Moneda de la transacción (`PEN`, `USD`). Mapea a `<cbc:DocumentCurrencyCode>`.
  * `vendedor`: Datos fiscales de ABC Software Corp (`RUC: 20556677889`). Mapea a `cac:AccountingSupplierParty`.
  * `comprador`: Datos fiscales del cliente adquiriente. Mapea a `cac:AccountingCustomerParty`.
  * `items`: Lista de líneas de factura con productos de abarrotes. Mapea a `cac:InvoiceLine`.
  * `totales`: Resumen monetario de tributos y totales a pagar. Mapea a `cac:TaxTotal` y `cac:LegalMonetaryTotal`.
  * `nro_documento_legado_origen`: Identificador de trazabilidad del vale informal o guía de almacén. Mapea a `cac:DespatchDocumentReference`.

### 1.2. ItemFactura (Línea de Venta de Abarrotes)
Cada uno de los bienes enajenados por la empresa.
* **Atributos**:
  * `codigo_producto`: Código interno del catálogo de abarrotes (ejemplo: `AB-ARR-001`).
  * `descripcion`: Glosa del bien (ejemplo: `Saco de Arroz Extra 50kg`).
  * `cantidad`: Unidades físicas despachadas.
  * `valor_unitario`: Precio neto unitario sin tributos.
  * `codigo_afectacion_igv`: Tipo de afectación según Catálogo 07 (ejemplo: `10` = Gravado - Operación Onerosa).
  * `codigo_sistema_isc`: Sistema de cálculo de ISC según **Catálogo 08 de SUNAT** (`01` = Al valor, `02` = Monto fijo, `03` = Precio de venta al público).
  * `isc_item`: Monto del ISC liquidado en el ítem.
  * `igv_item`: Monto del IGV liquidado en el ítem (18%).
  * `icbper_item`: Impuesto al consumo de bolsas plásticas (Ley N° 30884).

### 1.3. FichaAlmacenLegado (Entidad Histórica)
Registro documental informal del sistema anterior de inventarios.
* **Atributos**:
  * `fecha`: Fecha del movimiento.
  * `ingreso`: Unidades físicas ingresadas al inventario.
  * `salida`: Unidades físicas despachadas.
  * `producto`: Nombre libre del producto.
  * `nro_documento`: Identificador del vale interno (`VALE-SALIDA-0042`).

---

## 2. Invariantes y Reglas de Negocio del Dominio

### 2.1. Validación Estricta de RUC (Catálogo 06 SUNAT)
* **Regla**: El RUC del emisor y receptor debe ser una cadena numérica de exactamente 11 dígitos.
* **Prefijos Válidos**: Debe iniciar con `10` (persona natural con negocio) o `20` (persona jurídica).
* **Expresión Regular**: `^(10|20)\d{9}$`.
* **Excepción de Dominio**: Si el RUC no cumple con el formato, la operación es rechazada con el código `ERR-SUNAT-RUC`.

### 2.2. Validación Estricta del Catálogo 08 de SUNAT (Sistemas de ISC)
Para productos gravados con Impuesto Selectivo al Consumo (bebidas alcohólicas, gaseosas, energizantes comercializados por ABC Software Corp):
* **Valores Permitidos**:
  * `01`: Sistema al Valor (tasa porcentual sobre la base imponible).
  * `02`: Sistema Específico (monto fijo por unidad física / litro).
  * `03`: Sistema al Valor según Precio de Venta al Público sugerido.
* **Excepción de Dominio**: Si el campo `codigo_sistema_isc` contiene un valor no contemplado en el catálogo (ejemplo: `99`), se rechaza la transacción con `ERR-SUNAT-CAT08`.

### 2.3. Algoritmo de Cálculo Tributario
Para una línea de factura $i$ con valor unitario $V_u$ y cantidad $Q$:
1. **Base Imponible / Valor Venta**:
   $$VV_i = V_u \times Q$$
2. **Impuesto Selectivo al Consumo (ISC)**:
   $$\text{Si sistema = '01'}: ISC_i = VV_i \times Tasa_{ISC}$$
3. **Impuesto General a las Ventas (IGV - 18%)**:
   $$IGV_i = (VV_i + ISC_i) \times 0.18$$
4. **Impuesto a las Bolsas Plásticas (ICBPER)**:
   $$ICBPER_i = Q_{bolsas} \times S/\, 0.50$$
5. **Precio de Venta Total del Ítem**:
   $$Total_i = VV_i + ISC_i + IGV_i + ICBPER_i$$

### 2.4. Reglas de Redondeo Monetario
* Todo importe monetario se redondea a dos decimales según la regla estándar de SUNAT (mitad hacia arriba).
* La suma de los subtotales de las líneas debe ser matemáticamente consistente con los totales declarados en `totales` (`total_gravadas`, `total_igv`, `total_isc`, `total_icbper`, `importe_total`).

### 2.5. Trazabilidad de Almacén hacia Kardex Formal (RS N° 234-2006)
* Todo movimiento de salida registrado en el almacén de ABC Software Corp debe vincularse obligatoriamente a una `serie_numero` de comprobante de pago UBL 2.1.
* Los ingresos por reposición de stock se asientan en el Kardex formal con tipo de operación `02` (Compra nacional) sin generar comprobante de venta electrónica.
