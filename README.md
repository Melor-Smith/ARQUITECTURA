# ABC Software Corp — Especificaciones: Facturación Electrónica UBL 2.1 y Migración Legado

Repositorio de **solo especificaciones técnicas** (Spec-First): sin interfaz y sin código de implementación.
Normativa: **SUNAT RS N° 097-2012**, **Catálogo 08 (ISC)** y estándar **OASIS `UBL-Invoice-2.1.xsd`**.

---

## Índice de especificaciones entregadas

| # | Entregable | Archivo |
| :-: | :--- | :--- |
| 1 | Contrato OpenAPI 3.0 (Modelo de Dominio, DTOs y Endpoints) | [`specs/contracts/ubl-invoice-api.yaml`](specs/contracts/ubl-invoice-api.yaml) |
| 2 | Casos de uso tipo Nubefact (Gherkin) y **TABLA DE MATCH Legado <-> SUNAT Perú <-> OASIS UBL** | [`specs/features/001-facturacion-ubl-y-migracion.md`](specs/features/001-facturacion-ubl-y-migracion.md) |
| 3 | Decisiones arquitectónicas (MVC → Hexagonal, MSI/APK) | [`specs/adr/0001-mvc-a-hexagonal-y-multiplataforma.md`](specs/adr/0001-mvc-a-hexagonal-y-multiplataforma.md) |
| 4 | Diagramas: MVC, Hexagonal, Modelo de Dominio y distribución | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) |

Imágenes de los diagramas: [`docs/diagramas/`](docs/diagramas/) (PNG + código fuente `.mmd`).

---

## Endpoints especificados

| Método | Endpoint | Caso de uso | Respuestas |
| :---: | :--- | :--- | :---: |
| `POST` | `/api/v1/facturas` | Emite Factura Electrónica UBL 2.1 (valida RUC, IGV y Catálogo 08 ISC) | `201` / `400` |
| `GET` | `/api/v1/facturas/{serie_numero}` | Consulta estado, Hash CPE y XML UBL | `200` / `404` |
| `POST` | `/api/v1/migracion/fichas-legado` | Migra fichas del almacén legado a entidades trazables | `201` / `400` |

---

## Resumen de la TABLA DE MATCH (detalle completo en el archivo de features)

| Campo Sistema Legado | Modelo SUNAT Perú (DTO) | Nodo en `UBL-Invoice-2.1.xsd` | Catálogo / Regla SUNAT | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `nro_documento` | **`serie_numero`** | `<cbc:ID>` | Serie F + 3 dígitos, guion y correlativo de hasta 8 dígitos | `F001-000001` |
| `fecha` | `fecha_emision` | `<cbc:IssueDate>` | Formato `YYYY-MM-DD` | `2026-10-22` |
| Tipo de comprobante | `tipo_documento_codigo` | `<cbc:InvoiceTypeCode>` | Catálogo 01 | `01` |
| Moneda | `codigo_moneda` | `<cbc:DocumentCurrencyCode>` | Catálogo 02 | `PEN` |
| Vendedor / Comprador | `vendedor.*` / `comprador.*` | `cac:AccountingSupplierParty` / `cac:AccountingCustomerParty` | Catálogo 06 (RUC) | `20556677889` |
| `producto` / `salida` | `items[].descripcion` / `items[].cantidad` | `cac:Item/cbc:Description` / `cbc:InvoicedQuantity` | Anexo 1 RS 097-2012 | `Saco de Arroz Extra 50kg` / `2` |
| Afectación IGV | `items[].codigo_afectacion_igv` | `cbc:TaxExemptionReasonCode` | Catálogo 07 | `10` |
| Sistema de cálculo ISC | `items[].codigo_sistema_isc` | `cbc:TierRange` | **Catálogo 08**: 01 Al valor, 02 Monto fijo, 03 Precios venta público | `01` |
| Totales | `totales.importe_total` | `cac:LegalMonetaryTotal/cbc:PayableAmount` | Importe total | `236.00` |
