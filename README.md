# ABC Software Corp — Sistema de Facturación Electrónica UBL 2.1 y Migración Legado

Proyecto integral desarrollado bajo la metodología **Spec-Driven Development (Spec-First)**, adaptado al caso de estudio de **ABC Software Corp** (distribución de abarrotes y mercadería al por mayor y menor, migración de fichas informales de almacén, cumplimiento de la normativa **SUNAT RS N° 097-2012** y **RS N° 234-2006**, el **Catálogo 08 de SUNAT (Sistemas de ISC)** y el estándar internacional **OASIS UBL-Invoice-2.1.xsd**).

---

## 📌 Enlaces Directos a los Entregables Oficiales (Punto 4 del Examen)

| # | Entregable Oficial | Descripción Técnica | Enlace Directo |
| :-: | :--- | :--- | :--- |
| **1** | **Modelo de Dominio y Contratos** | DTOs tipados en Pydantic v2 y schemas OpenAPI sincronizados con identificador canónico `serie_numero` | [`src/models/schemas.py`](src/models/schemas.py)<br/>[`specs/contracts/ubl-invoice-api.yaml`](specs/contracts/ubl-invoice-api.yaml)<br/>[`specs/domain/modelo-dominio-tributario.md`](specs/domain/modelo-dominio-tributario.md) |
| **2** | **Diagramas de Arquitectura y Distribución** | Diagramas MVC Limpio, Evolución a Arquitectura Hexagonal y Estrategia de distribución Windows MSI y Android APK | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)<br/>[`specs/architecture/01-arquitectura-mvc-y-hexagonal.md`](specs/architecture/01-arquitectura-mvc-y-hexagonal.md)<br/>[`specs/adr/0001-decisiones-mvc-y-hexagonal.md`](specs/adr/0001-decisiones-mvc-y-hexagonal.md) |
| **3** | **Especificación OpenAPI 3.0 (YAML)** | Contrato canónico Spec-First (emisión Nubefact y migración de almacén con `serie_numero` -> `<cbc:ID>`) | [`specs/contracts/ubl-invoice-api.yaml`](specs/contracts/ubl-invoice-api.yaml) |
| **4** | **Matriz de Trazabilidad y Tabla de Match** | Cruce formal de 5 columnas: Legado ➔ SUNAT (Catálogo 8 ISC) ➔ OASIS UBL 2.1 ➔ DTO OpenAPI ➔ Tests | [`specs/features/001-proceso-abc-software-ubl.md`](specs/features/001-proceso-abc-software-ubl.md)<br/>[`specs/features/001-facturacion-ubl-y-migracion.md`](specs/features/001-facturacion-ubl-y-migracion.md) |
| **5** | **Mocks, Pruebas y Plantillas** | Banco de datos en memoria, plantillas XML UBL 2.1 y batería de 20 tests (Fase Roja ➔ Verde) | [`specs/templates/factura-ubl-2.1-template.xml`](specs/templates/factura-ubl-2.1-template.xml)<br/>[`tests/acceptance/test_facturacion_sdd.py`](tests/acceptance/test_facturacion_sdd.py)<br/>[`tests/unit/test_reglas_sunat.py`](tests/unit/test_reglas_sunat.py) |

---

## 📋 TABLA DE MATCH: LEGADO <-> SUNAT PERÚ <-> OASIS UBL-Invoice-2.1.xsd

Esta tabla formal constituye el contrato de transformación entre las fichas de almacén de **ABC Software Corp**, el modelo canónico tributario de **SUNAT** y el estándar internacional **OASIS UBL 2.1**:

| Campo Sistema Legado ABC Software Corp | Nombre en Modelo SUNAT Perú | Nodo / XPath exacto en OASIS UBL-Invoice-2.1.xsd | Catálogo / Regla Normativa SUNAT | Ejemplo Real de Negocio |
| :--- | :--- | :--- | :--- | :--- |
| `nro_documento` (salida comercial) | **`serie_numero`** | `/Invoice/cbc:ID` | **Regla Serie-Número SUNAT**: Serie alfanumérica `F` + 3 dígitos (`F001`) y correlativo de hasta 8 dígitos (`000001`). Catálogo 01 (`01` = Factura). | `F001-000001` |
| `nro_documento` (trazabilidad origen) | `nro_documento_legado_origen` | `/Invoice/cac:DespatchDocumentReference/cbc:ID` | **RS N° 097-2012 / RS N° 234-2006**: Trazabilidad entre el despacho físico de almacén y la factura electrónica. | `VALE-SALIDA-0042` |
| `fecha` | `fecha_emision` | `/Invoice/cbc:IssueDate` | Formato ISO 8601 `YYYY-MM-DD`. Consistente con período tributario. | `2026-10-22` |
| *(Hora de emisión)* | `hora_emision` | `/Invoice/cbc:IssueTime` | Formato ISO 8601 `hh:mm:ss`. Requerido en SUNAT UBL 2.1. | `10:30:00` |
| *(Definido por transacción)* | `codigo_moneda` | `/Invoice/cbc:DocumentCurrencyCode` | **Catálogo 02 SUNAT**: Códigos de Moneda (`PEN` = Soles, `USD` = Dólares). | `PEN` |
| *(RUC emisor ABC Software Corp)* | `vendedor.ruc` | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID` | **Catálogo 06 SUNAT**: Tipo de Documento de Identidad (`6` = RUC, 11 dígitos numéricos). | `20556677889` |
| *(Razón social emisor)* | `vendedor.razon_social` | `/Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | Nombre o denominación legal inscrita en RUC ante SUNAT. | `ABC SOFTWARE CORP S.A.C.` |
| *(RUC cliente)* | `comprador.ruc` | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID` | **Catálogo 06 SUNAT**: RUC (`6`) para facturas con derecho a crédito fiscal. | `20123456789` |
| *(Razón social cliente)* | `comprador.razon_social` | `/Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | Razón social del adquiriente en el padrón RUC. | `DISTRIBUIDORA DE ABARROTES EL SOL S.A.C.` |
| `producto` (glosa comercial) | `items[].descripcion` | `/Invoice/cac:InvoiceLine/cac:Item/cbc:Description` | Glosa o descripción detallada del bien enajenado. | `Saco de Arroz Extra 50kg` |
| `producto` (código de catálogo) | `items[].codigo_producto` | `/Invoice/cac:InvoiceLine/cac:Item/cac:SellersItemIdentification/cbc:ID` | Código interno único de inventario en ABC Software Corp. | `AB-ARR-001` |
| `salida` (unidades despachadas) | `items[].cantidad` | `/Invoice/cac:InvoiceLine/cbc:InvoicedQuantity` | Unidad de medida normalizada según **Catálogo 03 SUNAT** (`NIU` = Unidad, `KGM` = Kilogramo). | `10.00` |
| *(Precio de venta pactado / 1.18)* | `items[].valor_unitario` | `/Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount` | Valor venta unitario sin tributos. | `100.00` |
| *(Tipo de afectación tributaria)* | `items[].codigo_afectacion_igv` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID` | **Catálogo 07 SUNAT**: Códigos de Afectación al IGV (`10` = Gravado - Operación Onerosa). | `10` |
| *(Sistema de ISC en bebidas/licores)* | `items[].codigo_sistema_isc` | `/Invoice/cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TierRange` | **Catálogo 08 SUNAT**: Tipos de Sistema de Cálculo del ISC (`01` = Al valor, `02` = Monto fijo, `03` = Precio de venta al público). | `01` |
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

## 🏛️ Arquitectura de Software y Visión Hexagonal

El sistema sigue un diseño **MVC Desacoplado** listo para evolucionar hacia **Arquitectura Hexagonal (Ports & Adapters)**:
* **Controlador (`src/controllers/`)**: Enrutadores FastAPI y gestión de respuestas HTTP.
* **Modelo (`src/models/`, `src/services/`)**: Esquemas Pydantic v2, motor tributario SUNAT, validación de RUC (Catálogo 06), Catálogo 08 de ISC, IGV (18%), cálculo de Hash CPE SHA-256 y construcción de XML UBL 2.1.
* **Vista (`specs/contracts/ubl-invoice-api.yaml`)**: Serialización REST OpenAPI 3.0 y generación canónica de `UBL-Invoice-2.1.xsd`.
* **Persistencia (`src/repositories/`)**: Puerto de persistencia desacoplado consumiendo `tests/mocks/mock_db.py`.

Consulte la documentación técnica completa de arquitectura en:
* [`specs/architecture/01-arquitectura-mvc-y-hexagonal.md`](specs/architecture/01-arquitectura-mvc-y-hexagonal.md)
* [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)

---

## 🌐 Catálogo de Endpoints API (OpenAPI 3.0)

| Método | Endpoint | Caso de Uso | Respuestas |
| :---: | :--- | :--- | :---: |
| `POST` | `/api/v1/facturas` | Emite Factura Electrónica UBL 2.1 validando RUC y Catálogo 08 de ISC | `201 Created`<br/>`400 Bad Request` |
| `GET` | `/api/v1/facturas/{serie_numero}` | Consulta estado SUNAT, Hash CPE y XML UBL generado por `serie_numero` (`cbc:ID`) | `200 OK`<br/>`404 Not Found` |
| `POST` | `/api/v1/migracion/fichas-legado` | Migra registros históricos del almacén a entidades formales UBL y Kardex | `201 Created`<br/>`400 Bad Request` |
| `GET` | `/` | Health check del servicio y versión UBL activa | `200 OK` |
| `GET` | `/docs` | Interfaz interactiva Swagger UI | `200 OK` |

---

## 🚀 Instrucciones de Instalación y Ejecución

### 1. Clonar y preparar entorno virtual (Python 3.10+)
```bash
# Crear entorno virtual
python -m venv .venv

# Activar en Windows PowerShell
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Ejecutar la Batería de Pruebas (20 tests en Verde)
```bash
python -m pytest -v
```

### 3. Iniciar el Servidor de Desarrollo
```bash
python -m uvicorn src.main:app --reload --port 8000
```
La documentación interactiva estará disponible en: `http://localhost:8000/docs`.

---

## 🧪 Demostración del Ciclo SDD (Spec-Driven Development)

1. **Fase Roja (Red Phase)**:
   - Los contratos OpenAPI se definieron en `specs/contracts/ubl-invoice-api.yaml` y las especificaciones BDD en `specs/features/001-proceso-abc-software-ubl.md`.
   - Se crearon los tests de aceptación y unitarios antes de la implementación de código en `src/`.
   - `pytest` confirmó la ausencia previa de implementación.

2. **Fase Verde (Green Phase)**:
   - Se implementaron los modelos, repositorios, servicios, presentadores y controladores.
   - Resultado: **20 pruebas ejecutadas exitosamente (100% Passed)** sin dependencias de base de datos externas.
