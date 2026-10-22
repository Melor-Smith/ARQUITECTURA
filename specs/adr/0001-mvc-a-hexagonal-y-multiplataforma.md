# ADR 0001: Arquitectura MVC Desacoplada, Migración a Hexagonal y Distribución Multiplataforma

## Estado
**Aceptado** (Fecha: 2026-10-22)

---

## Contexto del Problema
La empresa **ABC Software Corp** cuenta con un software histórico básico de control de almacén que registra operaciones en fichas informales (`fecha`, `ingreso`, `salida`, `producto`, `nro_documento`). Con el objetivo de modernizar sus operaciones y cumplir con la normativa de comprobantes de pago electrónicos de la **SUNAT** (Resolución de Superintendencia N° 097-2012 y modificatorias), se requiere:
1. Implementar un motor de facturación electrónica compatible con el estándar internacional **OASIS UBL-Invoice-2.1.xsd** y los catálogos SUNAT (con énfasis en el **Catálogo 08 de ISC**).
2. Garantizar la trazabilidad y migración de las fichas informales hacia comprobantes fiscales válidos.
3. Permitir despliegues versátiles: desde una API centralizada en servidor hasta ejecutables locales para terminales de escritorio de almacén (Windows) y dispositivos de ruta/móviles (Android).

---

## Decisión de Arquitectura

### 1. Metodología Spec-Driven Development (Spec-First)
- **Decisión**: Escribir primero el contrato canónico OpenAPI 3.0.3 (`specs/contracts/ubl-invoice-api.yaml`) antes de cualquier línea de código de producción.
- **Justificación**: El contrato OpenAPI actúa como la única fuente de la verdad para el modelo de dominio, validaciones sintácticas, esquemas de entrada/salida y pruebas automatizadas (Fase Roja -> Fase Verde).

### 2. Patrón MVC Desacoplado con Visión a Arquitectura Hexagonal
- **Decisión**: Estructurar el código en capas:
  - `src/models/`: Modelos de Dominio y DTOs canónicos (Pydantic).
  - `src/views/`: Presentadores y serializadores de respuestas HTTP/JSON/XML.
  - `src/controllers/`: Enrutamiento y orquestación de peticiones FastAPI.
  - `src/services/`: Núcleo de lógica tributaria (validación de RUC, IGV 18%, Catálogo 08 de ISC, generación de XML UBL 2.1 y hash CPE).
  - `src/repositories/`: Puerto de abstracción de datos conectando a memoria (`tests/mocks/mock_db.py`).
- **Justificación**: Evita el clásico acoplamiento del MVC tradicional (donde el controlador conoce la base de datos). Facilita una transición limpia e incremental hacia **Arquitectura Hexagonal (Puertos y Adaptadores)** y Microservicios sin alterar la lógica de negocio ni romper los contratos expuestos.

### 3. Trazabilidad Estricta SUNAT y Catálogo 08 de ISC
- **Decisión**: Integrar en el motor tributario la validación de:
  - RUC de 11 dígitos con prefijo "10" o "20" (Catálogo 06).
  - Afectación al IGV (Catálogo 07).
  - Tipos de Sistema de Cálculo del Impuesto Selectivo al Consumo (Catálogo 08: `01` Al valor, `02` Monto fijo, `03` Precios de venta al público).
  - Estructura XML de `UBL-Invoice-2.1.xsd` con `cac:AccountingSupplierParty`, `cac:AccountingCustomerParty`, `cac:TaxTotal`, `cac:LegalMonetaryTotal` y cálculo de Hash CPE.

### 4. Estrategia de Distribución Multiplataforma (MSI y APK)
- **Decisión**:
  - **Windows**: Empaquetado binario autocontenido mediante PyInstaller y distribución corporativa mediante instalador MSI generado con WiX Toolset v4, con registro opcional de servicio en segundo plano y firma Authenticode.
  - **Android**: Distribución mediante APK/AAB nativo (con frontend móvil en Flutter/Kotlin o runtime embebido vía Chaquopy), soportando almacenamiento offline local y sincronización con el backend UBL.

---

## Consecuencias

### Positivas
- **Alineamiento Normativo Total**: Cumplimiento exhaustivo de la RS N° 097-2012 y especificaciones OASIS UBL 2.1.
- **Bajo Acoplamiento**: Los servicios y modelos de dominio no dependen de bases de datos externas ni de librerías de infraestructura pesadas.
- **Trazabilidad Garantizada**: Cada vale o guía del almacén legado se asocia mediante su correlativo en `nro_documento_legado_origen` y en `cac:DespatchDocumentReference`.
- **Flexibilidad de Despliegue**: Mismo núcleo de negocio utilizable en servidores Cloud, terminales Windows y dispositivos Android.

### Negativas / Mitigaciones
- **Complejidad del Esquema UBL 2.1**: Los comprobantes UBL exigen más de 30 campos obligatorios. *Mitigación*: Se utilizan schemas Pydantic con valores por defecto normativos y generador automático de XML UBL.
- **Mantenimiento de Mocks y Dependencias**: Mantener datos en memoria puede divergir si no se sincroniza con el YAML. *Mitigación*: Se aplica Spec-Driven Development riguroso donde los tests validan directamente contra los schemas del contrato OpenAPI.
