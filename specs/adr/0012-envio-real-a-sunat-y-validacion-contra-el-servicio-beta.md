# ADR 0012: Envío real a SUNAT y validación contra el servicio beta

- **Estado:** aceptado (2026-11-05).
- **Complementa:** ADR 0001 (hexagonal), ADR 0002 (XML desde el XSD) y ADR 0005 (códigos HTTP).

## Contexto

El puerto `ClienteOSE` tenía un único adaptador: `OseSimulada`. Esa OSE verifica la firma y el XSD, pero no aplica las reglas de validación de SUNAT, que son más de mil. Por eso nadie había comprobado que SUNAT aceptara los XML del sistema. "Valida contra el XSD" no implica "SUNAT lo acepta".

SUNAT ofrece un entorno de pruebas, el **servicio beta** `e-beta.sunat.gob.pe`, con estas condiciones:

- usa el mismo protocolo SOAP `sendBill` que producción;
- acepta cualquier RUC con el usuario `MODDATOS` y la clave `moddatos`;
- admite certificados autofirmados;
- no tiene efecto tributario.

## Decisión

1. **Adaptador `ClienteSunatSoap`** (`src/adapters/outbound/ose/sunat_soap.py`). Implementa el mismo puerto `ClienteOSE` sin dependencias nuevas: `urllib`, `zipfile` y `lxml`.
   - **Solicitud:** el XML firmado va en un ZIP, en Base64, dentro de `sendBill`, con autenticación WS-Security `UsernameToken` (RUC + usuario SOL).
   - **Respuesta:** el CDR se lee del ZIP que viene en `applicationResponse` (`ResponseCode`, `Description`, `Note`).
   - **Traducción de resultados a la aplicación:**

     | Respuesta de SUNAT | Resultado en la aplicación |
     |---|---|
     | CDR | `Cdr` (el dominio decide el estado) |
     | SOAP Fault 2000-3999 | `Cdr` RECHAZADO |
     | Excepciones de servicio (0100, 0109, 0130-0138, 0200), red caída o HTTP 401/429/5xx sin sobre SOAP | `OseNoDisponible`: el comprobante queda pendiente (202) y se reintenta |
     | Otras excepciones (credenciales, nombre de archivo) | `Cdr` con ese código, que la aplicación responde con 502 |
     | Cualquier otra cosa | `OseRespuestaInvalida` |

   - **Transporte inyectable**, para probar sin red.
2. **Selección por configuración** (`ABC_SUNAT_ENDPOINT`):
   - sin valor se usa la OSE simulada, como hasta ahora;
   - `beta` usa el servicio de pruebas de SUNAT;
   - `produccion` exige `ABC_CERTIFICADO_PFX` y un usuario SOL secundario real. Si faltan, la configuración falla al arrancar: el certificado autofirmado y `MODDATOS` no pueden llegar a producción por descuido.
3. **Tres niveles de prueba:**
   - **Sin red, en cada CI.** `test_cliente_sunat_soap.py` usa respuestas **reales grabadas** de beta: aceptación, rechazo 2335 por firma alterada y excepción 0161. `test_evidencia_sunat.py` vuelve a interpretar los CDR guardados y regenera los siete XML para exigir que sean idénticos a los que SUNAT aceptó (sin contar firma ni hora).
   - **En vivo, fuera de la CI principal.** `test_sunat_beta_en_vivo.py` y el workflow `sunat-beta.yml` corren a demanda y cada lunes. Dependen de la red, así que no bloquean un merge, pero avisan si SUNAT cambió una regla.
   - **Evidencia versionada.** `scripts/validar_en_sunat_beta.py` emite los siete comprobantes del caso por la API y guarda en `docs/evidencia-sunat/` lo enviado y lo respondido.

## Lo que encontró SUNAT

La primera vez, beta rechazó la factura FA01-1 (ISC e ICBPER) por dos defectos que la OSE simulada y el XSD dejaban pasar:

| Regla SUNAT | Defecto | Corrección |
|---|---|---|
| **3108** | El ISC de sistema 02 (monto fijo por unidad) no llevaba `cbc:Percent`. SUNAT verifica base × tasa = monto en los tres sistemas. | `Linea.tasa_isc_porcentual` informa la tasa equivalente monto / base con 5 decimales. |
| **3277** | La base global del IGV (`TaxSubtotal` 1000) sumaba el ISC. SUNAT exige la suma de los valores de venta gravados **sin** ISC. En la línea, en cambio, la base sí incluye el ISC. | El generador usa `totales.gravadas`. Ahora coincide también con el campo 14 del PLE 14.1, que ya era "sin ISC". |

Con ambas correcciones, **los siete comprobantes fueron aceptados (CDR código 0)**. Las dos reglas quedaron como pruebas de regresión en `tests/unit/generacion_xml/test_tributos.py`. Se comprobó por mutación que revertir cualquiera de las dos hace fallar la CI.

## Consecuencias

- La afirmación "SUNAT acepta lo que genera el sistema" pasa de supuesto a hecho verificado y reproducible.
- El caso de uso, el dominio y la API no cambiaron para soportar el envío real: es otro adaptador del mismo puerto.
- **Límites:**
  - **Beta no es producción:** no valida contra el padrón RUC y acepta certificados autofirmados. Producción usa el mismo adaptador, con certificado y usuario SOL reales.
  - **Boletas:** se envían una por una con `sendBill`, que SUNAT admite. El resumen diario (`sendSummary`, con ticket asíncrono) no está implementado.
  - **Firma del CDR:** el CDR de beta viene firmado con un certificado ficticio, así que su firma no se verifica. En producción habría que verificarla con el certificado de SUNAT.
