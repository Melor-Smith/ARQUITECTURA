# ADR 0005: Semántica HTTP, errores problem+json y seguridad

- **Estado:** aceptado.
- **Observación que atiende:** 7.

## Decisión

| Código | Cuándo |
|---|---|
| 200 | Consulta; reenvío exitoso; repetición idempotente de una emisión |
| 201 | Comprobante emitido **y** con CDR de la OSE. El estado sale del CDR (`ACEPTADO`, `ACEPTADO_CON_OBSERVACIONES` o `RECHAZADO`). Incluye `Location` |
| 202 | Comprobante registrado y firmado, pero la OSE no respondió: `PENDIENTE_ENVIO`. Incluye `Location` |
| 400 | **No cumple el esquema del contrato**: tipos, formatos, patrones, enumeraciones de catálogos, campos no permitidos, JSON mal formado |
| 401 | Falta el token Bearer o no es válido (`WWW-Authenticate: Bearer`) |
| 403 | El token no tiene el alcance requerido |
| 404 | El recurso no existe |
| 409 | Duplicado (vale ya migrado o ya facturado), `Idempotency-Key` reutilizada con otro contenido, reenvío de un comprobante que ya tiene CDR |
| 422 | **Cumple el esquema pero viola una regla**: RUC con módulo 11 inválido, factura sin RUC, serie que no corresponde al tipo, ISC mal configurado, saldo insuficiente, nota que excede el comprobante, fecha fuera de plazo… |
| 500 | Defecto interno (por ejemplo, un XML que no valida el XSD). No se exponen detalles |
| 502 | La OSE respondió algo que no es un CDR |
| 503 | La OSE no está disponible al reenviar (`Retry-After`) |

**Un único formato de error.** Todas las respuestas de error usan `application/problem+json` (RFC 9457), con:
- `type`, `title`, `status`, `detail` e `instance`;
- un `codigo` estable (`ERR-SUNAT-RUC`, `ERR-SUNAT-CAT08`, `ERR-KARDEX-SALDO-INSUFICIENTE`…);
- `errores[]` con el detalle por campo.

**Seguridad.**
- Token Bearer con alcances: `comprobantes:emitir`, `comprobantes:leer`, `inventario:escribir`, `inventario:leer` y `libros:leer`.
- El token se compara en tiempo constante.
- Los tokens se configuran con `ABC_API_TOKENS`; los tokens `dev-*` son solo para desarrollo.
- Migrar a OAuth2/JWT cambia únicamente `seguridad.py`.

## Consecuencias

- El cliente distingue "corrige el formato" (400) de "corrige el dato de negocio" (422) y de "reintenta más tarde" (202, 503).
- El 201 ya no promete una aceptación que no ocurrió.
