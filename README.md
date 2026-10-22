# ABC Software Corp — Sistema de Facturación Electrónica UBL 2.1 y Migración Legado

Proyecto integral desarrollado bajo la metodología **Spec-Driven Development (Spec-First)**, cumpliendo con la normativa de comprobantes de pago de la **SUNAT** (Resolución de Superintendencia N° 097-2012 y modificatorias), el **Catálogo 08 de SUNAT (Sistemas de ISC)** y el estándar internacional **OASIS UBL-Invoice-2.1.xsd**.

---

## 📌 Enlaces Directos a los Entregables Oficiales (Punto 4 del Examen)

| # | Entregable Oficial | Descripción Técnica | Enlace Directo |
| :-: | :--- | :--- | :--- |
| **1** | **Modelo de Dominio y Contratos** | DTOs tipados en Pydantic v2 y schemas OpenAPI sincronizados | [`src/models/schemas.py`](src/models/schemas.py)<br/>[`specs/contracts/ubl-invoice-api.yaml`](specs/contracts/ubl-invoice-api.yaml) |
| **2** | **Diagramas de Arquitectura y Distribución** | Diagramas Mermaid MVC Limpio, Evolución a Arquitectura Hexagonal y Estrategia de distribución Windows MSI y Android APK | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)<br/>[`specs/adr/0001-mvc-a-hexagonal-y-multiplataforma.md`](specs/adr/0001-mvc-a-hexagonal-y-multiplataforma.md) |
| **3** | **Especificación OpenAPI 3.0 (YAML)** | Contrato canónico Spec-First (casos de uso tipo Nubefact y migración de legados) | [`specs/contracts/ubl-invoice-api.yaml`](specs/contracts/ubl-invoice-api.yaml) |
| **4** | **Matriz de Trazabilidad Normativa** | Cruce exhaustivo: Datos Legado ➔ SUNAT (Catálogo 8 ISC) ➔ OASIS UBL-Invoice-2.1 ➔ DTO OpenAPI ➔ Test | [`specs/features/001-facturacion-ubl-y-migracion.md`](specs/features/001-facturacion-ubl-y-migracion.md) |
| **5** | **Mocks y Pruebas Automatizadas** | Banco de datos en memoria y batería de 20 tests (Fase Roja ➔ Fase Verde) | [`tests/mocks/mock_db.py`](tests/mocks/mock_db.py)<br/>[`tests/acceptance/test_facturacion_sdd.py`](tests/acceptance/test_facturacion_sdd.py)<br/>[`tests/unit/test_reglas_sunat.py`](tests/unit/test_reglas_sunat.py) |

---

## 🏛️ Arquitectura de Software

El sistema sigue un diseño **MVC Desacoplado** listo para evolucionar hacia **Arquitectura Hexagonal (Ports & Adapters)**:
- **`src/models/`**: Entidades del dominio y contratos DTO (Pydantic v2).
- **`src/views/`**: Presentadores de respuesta JSON/XML estandarizados.
- **`src/controllers/`**: Enrutadores FastAPI y orquestación de casos de uso.
- **`src/services/`**: Motor tributario SUNAT, validación de RUC (Catálogo 06), Catálogo 08 de ISC, IGV (18%), cálculo de Hash CPE SHA-256 y construcción de XML UBL 2.1.
- **`src/repositories/`**: Puerto de persistencia desacoplado consumiendo en memoria `tests/mocks/mock_db.py`.

---

## 🌐 Catálogo de Endpoints API (OpenAPI 3.0)

| Método | Endpoint | Caso de Uso | Respuestas |
| :---: | :--- | :--- | :---: |
| `POST` | `/api/v1/facturas` | Emite Factura Electrónica UBL 2.1 validando RUC y Catálogo 08 de ISC | `201 Created`<br/>`400 Bad Request` |
| `GET` | `/api/v1/facturas/{id_comprobante}` | Consulta estado SUNAT, Hash CPE y XML UBL generado | `200 OK`<br/>`404 Not Found` |
| `POST` | `/api/v1/migracion/fichas-legado` | Migra registros históricos del almacén legado a entidades UBL trazables | `201 Created`<br/>`400 Bad Request` |
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
   - Los contratos OpenAPI se definieron en `specs/contracts/ubl-invoice-api.yaml`.
   - Se crearon los tests de aceptación y unitarios antes de la implementación de código en `src/`.
   - `pytest` falló con 2 errores de recolección (`ModuleNotFoundError`), demostrando la ausencia previa de implementación.

2. **Fase Verde (Green Phase)**:
   - Se implementaron los modelos, repositorios, servicios, presentadores y controladores.
   - Resultado: **20 pruebas ejecutadas exitosamente (100% Passed)**.
