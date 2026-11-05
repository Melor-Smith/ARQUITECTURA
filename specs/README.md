# Especificaciones (spec-first)

| Carpeta / archivo | Contenido |
|---|---|
| [`features/001-facturacion-e-inventario.md`](features/001-facturacion-e-inventario.md) | Historias de usuario y escenarios Gherkin. Cada escenario tiene su prueba |
| [`traceability/matriz.yaml`](traceability/matriz.yaml) → [`matriz-trazabilidad.md`](traceability/matriz-trazabilidad.md) y [`matriz.csv`](traceability/matriz.csv) | **Matriz única**, generada con `python scripts/matriz.py`: sistema antiguo → SUNAT → XPath UBL 2.1 con la **cardinalidad calculada desde el XSD** → contrato → PLE 14.1 / 12.1 → código de error → prueba. Cada XPath se verifica contra XML generados |
| [`ple/formato-14.1.md`](ple/formato-14.1.md), [`ple/formato-12.1.md`](ple/formato-12.1.md) | Estructura campo por campo de los libros electrónicos |
| [`ple/anexo2/estructuras-ple-5.0.xls`](ple/anexo2/estructuras-ple-5.0.xls) | Excel oficial de SUNAT (Anexo 2 de la RS 286-2009, PLE 5.0); las pruebas comparan contra él la estructura del dominio |
| [`domain/modelo-dominio.md`](domain/modelo-dominio.md) | Objetos de valor, invariantes, fórmulas tributarias y estados |
| [`architecture/arquitectura.md`](architecture/arquitectura.md) | MVC dentro del hexágono, puertos y adaptadores, secuencia de emisión y diagrama de clases |
| [`adr/`](adr) | Decisiones de arquitectura 0001 a 0012 |
| [`contracts/openapi.yaml`](contracts/openapi.yaml) | Contrato OpenAPI **generado desde el código** y verificado por `tests/acceptance/test_contrato.py` |
| [`contracts/ubl-2.1/xsd/`](contracts/ubl-2.1/xsd) | XSD oficiales OASIS UBL 2.1 completos (maindoc + `common/`), usados para generar las clases y para validar |
| [`ejemplos/`](ejemplos) | Payloads válidos (alimentan los `examples` del OpenAPI y una prueba verifica que la API los acepta) y [`ejemplos/invalidos/`](ejemplos/invalidos): 16 contraejemplos, cada uno con el HTTP y el código de error esperados en `esperados.yaml` |

## Flujo de trabajo

1. Se describe el cambio en `features/` (Gherkin) y, si toca el contrato, en `ejemplos/` y en los DTO.
2. Se escribe la prueba (fase roja).
3. Se implementa en `src/domain` → `src/application` → `src/adapters` (fase verde).
4. `python scripts/exportar_openapi.py` regenera el contrato; `pytest` verifica que no haya divergencias.
