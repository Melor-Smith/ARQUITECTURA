# Índice Maestro de Especificaciones Técnicas (Specs)
## Proyecto: ABC Software Corp - Facturación Electrónica UBL 2.1 y Migración de Almacén
### Metodología: Spec-Driven Development (Spec-First)
### Normativa: SUNAT RS N° 097-2012, RS N° 234-2006 y OASIS UBL-Invoice-2.1.xsd

---

## 1. Estructura de Especificaciones Técnicas (`specs/`)

Toda la definición del sistema, contratos de interfaz, reglas de negocio y gobernanza técnica se encuentra organizada en las siguientes subcarpetas formales:

```
specs/
├── contracts/
│   └── ubl-invoice-api.yaml          # Contrato OpenAPI 3.0 (Identificador: serie_numero -> cbc:ID)
├── features/
│   ├── 001-proceso-abc-software-ubl.md# Historias de Usuario BDD y TABLA DE MATCH NORMATIVA EXHAUSTIVA
│   └── 001-facturacion-ubl-y-migracion.md # Criterios de aceptación y matriz de pruebas
├── architecture/
│   └── 01-arquitectura-mvc-y-hexagonal.md # Diseño MVC desacoplado y transición a Hexagonal
├── adr/
│   ├── 0001-decisiones-mvc-y-hexagonal.md # Justificación arquitectónica y distribución MSI / APK
│   └── 0001-mvc-a-hexagonal-y-multiplataforma.md # Registro fundacional de decisiones
├── domain/
│   └── modelo-dominio-tributario.md   # Entidades, RUC 11 dígitos, IGV 18%, ICBPER y Catálogo 08 ISC
├── templates/
│   ├── factura-ubl-2.1-template.xml   # Plantilla canónica XML UBL-Invoice-2.1.xsd
│   ├── factura-request-payload.json   # Payload de emisión para pruebas de API
│   └── ficha-almacen-legado.json      # Ficha informal de almacén para migración
└── README.md                          # Este índice maestro
```

---

## 2. Resumen de Componentes Clave

### 2.1. Contrato OpenAPI 3.0 (`specs/contracts/ubl-invoice-api.yaml`)
* Define los endpoints REST:
  * `POST /api/v1/facturas`: Emisión y validación normativa de facturas electrónicas.
  * `GET /api/v1/facturas/{serie_numero}`: Consulta de comprobante, Hash CPE y XML UBL generado.
  * `POST /api/v1/migracion/fichas-legado`: Procesamiento de fichas informales de inventario.
* **Normativa Clave**: El campo principal se denomina **`serie_numero`** y mapea de forma directa a `<cbc:ID>` en `UBL-Invoice-2.1.xsd` con formato SUNAT `F001-000001`.

### 2.2. Historias de Usuario y Tabla de Match (`specs/features/001-proceso-abc-software-ubl.md`)
* Casos de uso BDD en Gherkin cubriendo:
  * Emisión con IGV gravado (18%).
  * Validación del **Catálogo 08 de ISC** (`01` al valor, `02` monto fijo, `03` precio venta público).
  * Rechazos normativos por RUC inválido (código `ERR-SUNAT-RUC`).
  * Migración de vales de salida hacia series UBL y reposición de stock al Kardex formal RS N° 234-2006.
* **Tabla de Match**: Homologación exacta de 5 columnas entre Sistema Legado <-> Modelo SUNAT Perú <-> OASIS `UBL-Invoice-2.1.xsd`.

### 2.3. Arquitectura y Transición Hexagonal (`specs/architecture/01-arquitectura-mvc-y-hexagonal.md`)
* Diagramas Mermaid que detallan el desacoplamiento MVC en FastAPI.
* Estrategia de puertos y adaptadores para desacoplar el motor tributario del framework web y la base de datos.

### 2.4. Decisiones de Arquitectura - ADR (`specs/adr/0001-decisiones-mvc-y-hexagonal.md`)
* Registro formal de decisiones técnicas.
* Estrategia de distribución nativa:
  * **Windows MSI**: Paquete corporativo para puntos de venta POS mediante WiX Toolset v4 y PyInstaller.
  * **Android APK**: Aplicación móvil para almaceneros con soporte offline (SQLite) y sincronización central.

### 2.5. Modelo de Dominio Tributario (`specs/domain/modelo-dominio-tributario.md`)
* Entidades: `FacturaElectrónica`, `ItemFactura`, `FichaAlmacenLegado`.
* Invariantes de dominio: RUC de 11 dígitos numéricos, Catálogo 08 ISC, cálculo de IGV, ICBPER y reglas de redondeo.

### 2.6. Plantillas de Referencia (`specs/templates/`)
* Ejemplos completos en XML canónico UBL 2.1 y payloads JSON para verificación rápida e interoperabilidad con OSEs.
