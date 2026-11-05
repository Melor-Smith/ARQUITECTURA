# ADR 0006: Contrato OpenAPI generado desde el código y verificado en CI

- **Estado:** **reemplazado por el [ADR 0013](0013-contrato-escrito-primero-y-verificado-contra-el-codigo.md)** (2026-11-05). Se conserva como registro: explica por qué el contrato pasó un tiempo generándose desde el código.
- **Observaciones que atiende:** 1.4 y 4. El YAML decía `\d{1,8}` y el código `\d{6}`, y el payload de ejemplo era rechazado.

## Contexto

Mantener a mano un YAML y unos DTO en paralelo hizo que divergieran: el README afirmaba una "correspondencia 1:1 exacta" que no existía.

## Decisión

1. Los DTO de Pydantic (`adapters/inbound/http/esquemas.py`) son la **única definición** del contrato. FastAPI genera el OpenAPI 3.1.
2. `specs/contracts/openapi.yaml` es la copia versionada y revisable en los PR. Se regenera con `python scripts/exportar_openapi.py`.
3. `tests/acceptance/test_contrato.py` verifica que:
   - el YAML versionado sea **idéntico** al generado;
   - **todos** los ejemplos de `specs/ejemplos/*.json` sean aceptados por la API (esos mismos archivos alimentan los `examples` del OpenAPI);
   - toda respuesta 4xx o 5xx se documente como `application/problem+json`.
4. El flujo se mantiene *spec-first*. Un cambio de contrato se propone primero modificando DTO, ejemplos y Gherkin en el PR, y la prueba de contrato obliga a regenerar el YAML.

## Consecuencias

El contrato y el código ya no pueden divergir sin que falle CI.

## Por qué se reemplazó

Esta decisión resolvió la divergencia, pero invirtió la autoría: el código definía el contrato y el YAML era una copia con el aviso "GENERADO". Eso es *code-first*, aunque el punto 4 dijera lo contrario. El ADR 0013 conserva la garantía (contrato y código no pueden divergir sin que falle la CI) y devuelve la autoría al contrato.
