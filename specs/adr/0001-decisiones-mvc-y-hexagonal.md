# ADR 0001: Arquitectura MVC Desacoplada, Evolución a Arquitectura Hexagonal y Estrategia de Distribución Multiplataforma (MSI y APK)

## Estado
**Aceptado**

## Contexto del Proyecto
**ABC Software Corp** es una empresa de distribución mayorista y minorista de abarrotes y mercadería general. La empresa enfrenta tres desafíos fundamentales:
1. **Dispersión Operativa en Almacén**: Existencia de fichas informales con campos planos (`fecha`, `ingreso`, `salida`, `producto`, `nro_documento`) sin control tributario formal.
2. **Exigencia Normativa de SUNAT**: Obligación de emitir comprobantes de pago electrónicos bajo la **RS N° 097-2012/SUNAT**, estándar **OASIS UBL-Invoice-2.1.xsd**, y cumplimiento del **Catálogo 08 de ISC** en productos gravados, además del registro de inventario permanente según la **RS N° 234-2006**.
3. **Diversidad de Dispositivos**: La solución debe ejecutarse en estaciones fijas de caja en Windows (POS) y terminales móviles de despacho en Android para operarios de almacén.

---

## Decisiones Tomadas

### 1. Metodología Spec-Driven Development (SDD / Spec-First)
- **Decisión**: La especificación técnica formal (Contrato OpenAPI 3.0 en `specs/contracts/ubl-invoice-api.yaml` y Gherkin BDD en `specs/features/001-proceso-abc-software-ubl.md`) antecede a cualquier implementación de software.
- **Justificación**: Garantiza la concordancia absoluta con los esquemas tributarios de SUNAT y la interoperabilidad con OSEs y software legado.

### 2. Arquitectura MVC Desacoplada en FastAPI
- **Decisión**: Estructurar la aplicación en Modelo-Vista-Controlador desacoplado:
  - **Controlador (`src/controllers/`)**: Endpoints FastAPI sin lógica de negocio, encargados de la negociación HTTP y enrutamiento.
  - **Modelo (`src/models/`, `src/services/`, `src/repositories/`)**: Encapsula las entidades de dominio, validadores de schemas Pydantic, cálculo de tributos (IGV 18%, ISC Catálogo 08, ICBPER) y generación canónica del XML UBL 2.1.
  - **Vista**: Serialización OpenAPI 3.0 para consumo REST y generación de XML según el esquema OASIS `UBL-Invoice-2.1.xsd`.
- **Justificación**: Permite un desarrollo ágil, pruebas unitarias y de integración inmediatas, manteniendo cero acoplamiento con librerías de interfaz gráfica.

### 3. Evolución hacia Arquitectura Hexagonal (Ports & Adapters)
- **Decisión**: Las capas de servicio y repositorio se diseñan con interfaces explícitas que permitirán migrar a Puertos y Adaptadores cuando la solución requiera múltiples motores de base de datos o colas de mensajería asíncronas.
- **Mapeo de Nomenclatura Normativa**:
  - El campo principal del comprobante en el contrato de API se denomina explícitamente **`serie_numero`**, que mapea de forma unívoca a `<cbc:ID>` en el estándar OASIS UBL 2.1 con el formato SUNAT `F001-000001`.

### 4. Estrategia de Distribución Nativa Multiplataforma

#### Windows Desktop (Instalador MSI)
- **Tecnología**: Binario autocontenido generado mediante PyInstaller y empaquetado formal con **WiX Toolset v4**.
- **Ventajas para ABC Software Corp**:
  - Instalación corporativa estandarizada en terminales POS de ventas.
  - Despliegue automatizado mediante políticas de grupo (GPO) de Windows Server / Active Directory.
  - Sin necesidad de instalar Python o dependencias externas en las máquinas de las sucursales.
  - Capacidad de ejecutarse como servicio en segundo plano para sincronizaciones nocturnas.

#### Android Mobile (Paquete APK / AAB)
- **Tecnología**: Aplicación nativa en Flutter/Kotlin con motor de reglas tributarias ejecutado localmente vía Chaquopy o consumo de la API REST local/cloud.
- **Ventajas para ABC Software Corp**:
  - Terminales de mano para almaceneros que registran ingresos y salidas in situ.
  - Soporte de escáner de código de barras para los abarrotes.
  - Almacenamiento local SQLite con cifrado (SQLCipher) que permite operar en zonas de almacén sin cobertura Wi-Fi y sincronizar automáticamente con el backend central al recuperar conexión.

---

## Consecuencias y Beneficios

### Positivas
- **Alineamiento Normativo Total**: 100% de cumplimiento con SUNAT RS N° 097-2012, RS N° 234-2006 y OASIS UBL-Invoice-2.1.xsd.
- **Trazabilidad Garantizada**: Cada movimiento de almacén informal se asocia a su comprobante UBL mediante el nodo `cac:DespatchDocumentReference`.
- **Mantenibilidad y Testeabilidad**: Cobertura completa de pruebas unitarias y de aceptación (Fase Roja -> Fase Verde) sin dependencias externas complejas.
- **Flexibilidad Operativa**: Misma lógica de negocio en estaciones Windows y terminales móviles Android.

### Mitigaciones de Riesgo
- **Complejidad del XML UBL**: Se mitiga mediante servicios modulares de generación XML (`SunatUBLService`) con validación de hash SHA-256 previa a la emisión.
