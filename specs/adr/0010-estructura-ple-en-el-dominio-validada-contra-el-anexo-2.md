# ADR 0010: Estructura de los TXT del PLE en el dominio, validada contra el Anexo 2 oficial

- **Estado:** aceptado (2026-11-05).
- **Reemplaza:** el punto 5 del ADR 0007 ("el TXT con `|` es una vista").

## Contexto

Al contrastar los TXT con el Excel oficial de SUNAT (Anexo 2 de la RS 286-2009, PLE 5.0) aparecieron defectos que ninguna prueba detectaba, porque las pruebas solo verificaban lo que el propio código generaba:

| Defecto | Efecto en el programa PLE |
|---|---|
| El 12.1 tenía 17 campos. Faltaban el 8 y el 9 (catálogo UNSPSC/GTIN, vigentes desde 2021) | Archivo rechazado: todos los campos desde el 8 quedaban corridos |
| Las salidas del 12.1 iban en positivo | El campo 18 exige negativo o `0.00` |
| En un libro vacío, el nombre del archivo ponía `0` en la posición 30 | `0` significa "cierre de operaciones, baja del RUC" |
| El campo 5 del 14.1 llevaba cualquier vencimiento | Solo se acepta hasta el último día del mes siguiente al periodo |
| Boleta a cliente no identificado: tipo de documento `0` | El PLE no acepta `0`; el campo debe ir vacío |
| El texto podía llevar `/` o `\`, y los campos alfanuméricos espacios o tildes | Caracteres no permitidos |

La causa de fondo: la estructura estaba **implícita** en el orden de los atributos de un dataclass y en una vista que convertía cada valor sin saber de qué campo se trataba.

## Decisión

1. **La estructura es un dato del dominio** (`src/domain/ple_estructura.py`). Cada `Campo` lleva su número, el atributo que lo alimenta, su tipo (numérico, texto, alfanumérico, fecha, importe o tipo de cambio), su longitud, su obligatoriedad y las reglas adicionales del Anexo 2.
   - El layout del TXT lo fija la norma; no es un detalle de presentación.
   - Sigue siendo solo stdlib, así que se respeta la regla de dependencias.
2. **El formato depende del tipo del campo:**
   - fechas en `DD/MM/AAAA`;
   - importes con 2 decimales, `ROUND_HALF_UP` y nunca `-0.00`;
   - tipo de cambio con 3 decimales;
   - texto limpio de `| / \` y cortado a su longitud;
   - alfanuméricos sin tildes y solo con los caracteres permitidos.
3. **Validación antes de entregar.** `contenido_txt` valida:
   - cada campo: tipo, longitud y obligatoriedad;
   - las reglas entre campos de la columna "Observaciones".

   Si algo incumple, levanta `EstructuraPleInvalida`, que la API devuelve como 422 `ERR-PLE-ESTRUCTURA` con la línea, el campo y el motivo. **Nunca se entrega un TXT que el PLE rechazaría.**
4. **La fuente oficial queda versionada** en `specs/ple/anexo2/estructuras-ple-5.0.xls`. Una prueba lee ese Excel y compara, campo por campo, el número, el tipo, la longitud y la obligatoriedad, además de la plantilla del nombre del archivo. Si SUNAT publica otra versión, se reemplaza el Excel y las pruebas señalan qué cambió.
5. **La vista HTTP solo empaqueta** el TXT, con su `Content-Disposition` y su nombre oficial. La vista JSON usa el mismo formateador, así que ambas vistas no pueden divergir.

## Consecuencias

- Los defectos de la tabla quedaron corregidos y cada uno tiene su prueba (`tests/unit/ple/`).
- Una plantilla del 14.1 con 36 columnas, que divide el campo 30 en dos, se detecta como inválida (`test_estructura_de_36_columnas_no_es_la_del_anexo_2`). El análisis está en `specs/ple/formato-14.1.md`.
- `xlrd` se agrega solo como dependencia de desarrollo, para leer el `.xls` en las pruebas.
- **Validación con el programa oficial (05/11/2026).** El 12.1 generado por el sistema pasó el PLE 5.2.0.7 **sin inconsistencias**, en la tercera ronda. Las dos primeras rondas encontraron dos reglas más, que se incorporaron al dominio y al validador propio:
  - unidad UN/ECE en el campo 16;
  - las operaciones 01 a 06 no admiten documento `00`.

  Ver [`docs/evidencia-ple/`](../../docs/evidencia-ple/README.md).
- **Fuera de alcance:**
  - las validaciones del programa PLE que dependen del padrón RUC o de la estructura 1 (tipo de cambio diario);
  - cargar los TXT en el validador de escritorio de SUNAT, que es un paso manual pendiente.
