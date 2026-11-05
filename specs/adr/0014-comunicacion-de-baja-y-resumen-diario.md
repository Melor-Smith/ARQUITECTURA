# ADR 0014: Comunicación de baja y resumen diario (contrato antes que el código)

- **Estado:** aceptado (2026-11-05). **Contrato especificado; implementación pendiente.**
- **Depende de:** ADR 0012 (envío real a SUNAT) y ADR 0013 (contrato escrito primero).

## Contexto

Hoy el sistema emite y envía comprobantes uno por uno con `sendBill`, pero no puede **anular** una factura mal emitida, por ejemplo con el RUC del adquiriente equivocado. Es un caso de uso real y frecuente en una distribuidora: el cajero se equivoca y la factura ya llegó a SUNAT.

SUNAT resuelve la anulación con dos documentos resumen. Ninguno de los dos se responde en el momento:

| Documento | Para qué | Servicio SOAP | Respuesta |
|---|---|---|---|
| **Comunicación de baja** (UBL `VoidedDocuments`, id `RA-AAAAMMDD-n`) | Anular facturas y las notas que las modifican | `sendSummary` | Un **ticket**. El CDR se consulta después con `getStatus` |
| **Resumen diario** (UBL `SummaryDocuments`, id `RC-AAAAMMDD-n`) | Informar las boletas de un día y anular boletas (estado 3) | `sendSummary` | Un **ticket**, igual que la baja |

## Decisión

1. **El contrato se escribe primero y se versiona como planificado** (ADR 0013). Todas las operaciones y esquemas llevan `x-estado: planificado`:

   | Operación | Cuerpo | Respuesta |
   |---|---|---|
   | `POST /api/v1/comprobantes/{tipo_comprobante}/{serie_numero}/bajas` | [`baja.schema.json`](../contracts/schemas/baja.schema.json): `motivo` (1-100 caracteres) | **202** `TramiteSunatSalida` con el ticket y `Location: /api/v1/bajas/{id}` |
   | `GET /api/v1/bajas/{id}` | — | 200 con el estado; si sigue `EN_PROCESO`, el servidor consulta `getStatus` |
   | `POST /api/v1/resumenes-diarios` | [`resumen-diario.schema.json`](../contracts/schemas/resumen-diario.schema.json): `fecha_referencia` y `anular[]` | **202** `TramiteSunatSalida` y `Location: /api/v1/resumenes-diarios/{id}` |
   | `GET /api/v1/resumenes-diarios/{id}` | — | 200 con el estado y, al terminar, el CDR |

   Los ejemplos están en [`specs/ejemplos/planificados/`](../ejemplos/planificados) y una prueba verifica que cumplen el schema.

2. **Códigos HTTP**, con la misma semántica del ADR 0005:
   - **202:** el trámite es asíncrono porque SUNAT responde con un ticket.
   - **409:** el comprobante no está `ACEPTADO` o ya tiene una baja en curso.
   - **422** con estos códigos:
     - `ERR-SUNAT-BAJA-PLAZO`: venció el plazo de la baja;
     - `ERR-SUNAT-BAJA-BOLETA`: una boleta se anula en el resumen diario, no aquí;
     - `ERR-SUNAT-RESUMEN-VACIO`: no hay boletas en esa fecha.
   - **503:** SUNAT no responde. El trámite queda `PENDIENTE_ENVIO` y se reintenta, como en el ADR 0012.

3. **Diseño previsto de la implementación** (hexagonal, sin tocar lo existente):
   - **Dominio:** agregado `TramiteSunat` con la máquina de estados `PENDIENTE_ENVIO → EN_PROCESO → ACEPTADO | RECHAZADO`. Al aceptarse la baja, el `Comprobante` pasa a `DADO_DE_BAJA` y se revierte su salida del Kardex, como hoy con un CDR de rechazo.
   - **Puerto nuevo `ClienteResumenesSunat`** con dos operaciones: `enviar_resumen(xml) -> ticket` y `consultar_ticket(ticket) -> Cdr | EnProceso`. Su adaptador reutiliza el transporte SOAP y la firma de `ClienteSunatSoap`.
   - **XML:** se generan clases `xsdata` de los XSD de SUNAT para `VoidedDocuments` y `SummaryDocuments`, igual que con UBL (ADR 0002).
   - **PLE 14.1:** la anotación de un comprobante dado de baja cambia de estado (campo 35). La regla exacta se fijará contra el Excel del Anexo 2, que ya está en el repositorio (ADR 0010).
   - **Plazos:** los plazos de la baja y del resumen se configuran (`ABC_PLAZO_BAJA_DIAS`, `ABC_PLAZO_RESUMEN_DIAS`) y se fijan contra la norma vigente de SUNAT antes de implementar. No se escriben a mano en el código.

4. **Criterio de "terminado":** quitar `x-estado: planificado`. Desde ese momento, el comparador del ADR 0013 exige que el código implemente exactamente lo especificado.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| `DELETE /comprobantes/{id}` | Un comprobante electrónico no se borra: la baja es un **nuevo documento** que SUNAT acepta o rechaza. `DELETE` sugiere un efecto inmediato que no existe |
| Respuesta 200 síncrona que espera el CDR | `getStatus` puede tardar minutos y la solicitud HTTP expiraría. El patrón 202 + `Location` + consulta es el estándar para trámites asíncronos |
| Anular boletas con comunicación de baja | SUNAT anula las boletas en el resumen diario con estado 3. Mezclar ambos flujos produciría rechazos |

## Consecuencias

- El caso de uso de anulación queda **especificado, revisable y probado a nivel de contrato** antes de escribir código. Quien implemente parte de un contrato ya acordado.
- El README deja de declarar "no implementado" sin más: declara "especificado en el ADR 0014, implementación pendiente".
