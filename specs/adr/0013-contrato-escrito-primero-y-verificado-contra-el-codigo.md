# ADR 0013: Contrato escrito primero y verificado contra el código

- **Estado:** aceptado (2026-11-05).
- **Reemplaza:** [ADR 0006](0006-contrato-openapi-generado-y-verificado.md) (contrato generado desde el código).
- **Observaciones que atiende:** la revisión del 05/11 señaló que el ADR 0006 era *code-first*: los DTO de Pydantic eran "la única definición del contrato" y el YAML llevaba el aviso "GENERADO desde el código. No editar a mano".

## Contexto

El curso evalúa **Spec-First**: el contrato se escribe antes que el código, y el código lo implementa.

La historia del contrato tiene tres etapas:

1. **Primer entregable (22/10).** El YAML y el código se escribieron a mano y por separado, y divergieron: el YAML decía `\d{1,8}` y el código `\d{6}` (observación 1.4).
2. **ADR 0006.** Se generó el YAML desde el código para que no pudieran divergir. Resolvió la divergencia, pero dejó al código como autor del contrato.
3. **Este ADR.** Se conserva la garantía de la etapa 2 y se devuelve la autoría al contrato. Es una evolución: primero se aseguró que contrato y código no pudieran divergir y después se invirtió la dirección.

## Decisión

1. **El contrato son archivos escritos a mano** en `specs/contracts/`:

   | Archivo | Qué define |
   |---|---|
   | `schemas/comprobante-emision.schema.json` | Unión factura / boleta / nota de crédito / nota de débito, discriminada por `tipo_comprobante` (Catálogo 01) |
   | `schemas/linea.schema.json` | Línea del comprobante y configuración del ISC (Catálogo 08) |
   | `schemas/forma-pago.schema.json` | Contado o crédito con cuotas (RS 193-2020) |
   | `schemas/ficha-legado.schema.json` · `schemas/lote-fichas.schema.json` | Ficha del sistema antiguo y migración por lotes |
   | `schemas/problema.schema.json` | Error RFC 9457 |
   | `schemas/catalogos.schema.json` · `schemas/tipos.schema.json` | Catálogos SUNAT y tablas PLE soportados; importes y cantidades decimales |
   | `schemas/baja.schema.json` · `schemas/resumen-diario.schema.json` | Operaciones planificadas ([ADR 0014](0014-comunicacion-de-baja-y-resumen-diario.md)) |
   | `openapi.yaml` | Rutas, parámetros, códigos HTTP, seguridad y esquemas de respuesta. Referencia los JSON Schemas con `$ref: schemas/...` |

   Son JSON Schema 2020-12, el dialecto de OpenAPI 3.1. Cada propiedad lleva en su `description` la regla SUNAT y la fila de la matriz de trazabilidad (p. ej. "Catálogo 03 ... Matriz T32"). Una prueba falla si una propiedad no está documentada.

2. **El contrato se edita primero.** Un cambio de campo, catálogo, patrón o límite empieza en `specs/contracts/`. La prueba de contrato falla (fase roja) hasta que el DTO de `esquemas.py` lo implementa (fase verde).

3. **La dirección de las pruebas se invierte** (`tests/acceptance/test_contrato.py`):
   - cada JSON Schema es válido y cada ejemplo de `specs/ejemplos/` lo cumple;
   - **el contrato define qué es 400 y qué es 422**: los contraejemplos que esperan 400 no cumplen el schema, y los que esperan 422 sí lo cumplen (son reglas de negocio);
   - **el código implementa exactamente el contrato.** `scripts/contrato.py` resuelve los `$ref` externos y compara el contrato con el OpenAPI que publica FastAPI, campo por campo. Revisa rutas, parámetros, códigos HTTP, tipos de contenido, campos, obligatorios, `additionalProperties`, catálogos, patrones, longitudes, límites numéricos y valores por defecto. La comprobación es en las dos direcciones: el código no puede tener ni más ni menos que el contrato;
   - por cada par DTO ↔ schema, los campos y los obligatorios son los mismos.

4. **`scripts/exportar_openapi.py` ya no genera nada.** Lista las diferencias entre el contrato y el código, y opcionalmente guarda el OpenAPI del código en `build/` para inspeccionarlo. No es el contrato.

5. **Lo planificado también es contrato.** Una operación o esquema con `x-estado: planificado` está especificado pero aún no implementado: el comparador no exige que exista en el código. Si se implementa sin quitar la marca, la prueba falla.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Mantener el ADR 0006 (generado desde el código) | Es *code-first*. El contrato no puede revisarse ni acordarse antes de que exista el código |
| Generar los DTO de Pydantic desde los JSON Schemas (`datamodel-code-generator`) | Es spec-first puro, pero los DTO generados pierden las reglas que hoy expresan (unión discriminada, `extra="forbid"`, `Decimal` con `decimal_places`) y habría que reescribir el adaptador HTTP. La comparación en CI da la misma garantía con menos riesgo |
| Validar las solicitudes en tiempo de ejecución contra el YAML (middleware) | Duplica la validación de Pydantic y hace más lenta cada solicitud. La garantía se obtiene una vez en la CI, no en cada solicitud |

## Consecuencias

- El contrato se puede leer, revisar y acordar sin abrir Python. Los JSON Schemas sirven a cualquier cliente (la app Android del ADR 0008, por ejemplo) para validar antes de enviar.
- Contrato y código siguen sin poder divergir: la CI falla y `python scripts/exportar_openapi.py` dice exactamente qué difiere.
- El `openapi.yaml` inicial se obtuvo **una sola vez** del OpenAPI ya verificado del commit `46b375e`, para no perder lo que ya estaba probado. Desde este ADR se mantiene a mano.
- Los importes decimales se describen como `["number", "string"]`. El contrato fija además el formato de la cadena (hasta N decimales); el código lo exige con `decimal_places`. El comparador no compara ese patrón, porque Pydantic no lo publica.
