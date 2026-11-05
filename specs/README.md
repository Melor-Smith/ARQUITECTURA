# Especificaciones (spec-first)

| Carpeta / archivo | Contenido |
|---|---|
| [`features/001-facturacion-e-inventario.md`](features/001-facturacion-e-inventario.md) | Historias de usuario y escenarios Gherkin. Cada escenario tiene su prueba |
| [`traceability/matriz.yaml`](traceability/matriz.yaml) → [`matriz-trazabilidad.md`](traceability/matriz-trazabilidad.md) y [`matriz.csv`](traceability/matriz.csv) | **Matriz única**, generada con `python scripts/matriz.py`: sistema antiguo → SUNAT → XPath UBL 2.1 con la **cardinalidad calculada desde el XSD** → contrato → PLE 14.1 / 12.1 → código de error → prueba. Cada XPath se verifica contra XML generados |
| [`ple/formato-14.1.md`](ple/formato-14.1.md), [`ple/formato-12.1.md`](ple/formato-12.1.md) | Estructura campo por campo de los libros electrónicos |
| [`ple/anexo2/estructuras-ple-5.0.xls`](ple/anexo2/estructuras-ple-5.0.xls) | Excel oficial de SUNAT (Anexo 2 de la RS 286-2009, PLE 5.0); las pruebas comparan contra él la estructura del dominio |
| [`domain/modelo-dominio.md`](domain/modelo-dominio.md) | Objetos de valor, invariantes, fórmulas tributarias y estados |
| [`architecture/arquitectura.md`](architecture/arquitectura.md) | MVC dentro del hexágono, puertos y adaptadores, secuencia de emisión y diagrama de clases |
| [`adr/`](adr) | Decisiones de arquitectura 0001 a 0014 (la 0006 quedó reemplazada por la 0013 y se conserva como historial) |
| [`contracts/openapi.yaml`](contracts/openapi.yaml) | Contrato OpenAPI 3.1 **escrito a mano y editado primero** ([ADR 0013](adr/0013-contrato-escrito-primero-y-verificado-contra-el-codigo.md)): rutas, códigos HTTP, seguridad y respuestas. `tests/acceptance/test_contrato.py` falla si el código no lo implementa exactamente |
| [`contracts/schemas/`](contracts/schemas) | **JSON Schemas 2020-12 escritos a mano**, uno por DTO de entrada más el error RFC 9457. Cada propiedad cita su regla SUNAT y su fila de la matriz. Incluye los de baja y resumen diario, planificados ([ADR 0014](adr/0014-comunicacion-de-baja-y-resumen-diario.md)) |
| [`contracts/ubl-2.1/xsd/`](contracts/ubl-2.1/xsd) | XSD oficiales OASIS UBL 2.1 completos (maindoc + `common/`), usados para generar las clases y para validar |
| [`ejemplos/`](ejemplos) | Payloads válidos (cumplen los JSON Schemas, van como `examples` en el OpenAPI y una prueba verifica que la API los acepta), [`ejemplos/planificados/`](ejemplos/planificados) (baja y resumen diario) y [`ejemplos/invalidos/`](ejemplos/invalidos): 16 contraejemplos, cada uno con el HTTP y el código de error esperados en `esperados.yaml` |

## Flujo de trabajo

1. Se describe el cambio en `features/` (Gherkin) y, si toca la API, **primero en el contrato**: `contracts/schemas/*.schema.json`, `contracts/openapi.yaml` y `ejemplos/`.
2. Se escribe la prueba de negocio. La de contrato ya falla sola, porque el código todavía no implementa lo nuevo (fase roja).
3. Se implementa en `src/domain` → `src/application` → `src/adapters`, incluidos los DTO de `esquemas.py` (fase verde).
4. `python scripts/exportar_openapi.py` lista lo que aún difiere entre el contrato y el código; `pytest` lo exige en la CI.
