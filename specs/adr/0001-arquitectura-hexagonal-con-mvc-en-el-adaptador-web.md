# ADR 0001: Arquitectura hexagonal con MVC dentro del adaptador web

- **Estado:** aceptado (2026-11-04). Reemplaza a los dos ADR "0001" de la versión anterior.
- **Observaciones que atiende:** 8a a 8e (transición inviable, MVC mal entendido).

## Contexto

La versión anterior decía ser "MVC preparado para hexagonal", pero no lo era:
- el servicio era estático y usaba el repositorio concreto;
- el código de producción importaba de `tests/mocks`;
- el "modelo" eran DTOs de Pydantic;
- la "vista" era el YAML de OpenAPI.

Ninguno de los puertos dibujados existía. Además, la solución debe correr en una API central, en puntos de venta Windows (MSI) y en terminales Android (APK). Eso exige que las reglas tributarias no dependan del framework web ni de la base de datos.

## Decisión

1. **Tres capas con dependencias hacia adentro.**
   - `src/domain`: solo la biblioteca estándar.
   - `src/application`: casos de uso y puertos como `typing.Protocol`.
   - `src/adapters`: entrada HTTP; salida a persistencia, UBL, firma, OSE y reloj.
2. **Raíz de composición única** (`src/bootstrap.py`). Los casos de uso reciben todas sus dependencias por constructor; no hay estado global.
3. **MVC queda dentro del adaptador HTTP.**
   - Controladores: traducen HTTP ↔ comando.
   - Modelo: aplicación + dominio.
   - Vistas: representaciones JSON, XML firmado y TXT del PLE.
   - El OpenAPI es el **contrato** que describe esas vistas, no una vista.
4. **El dominio tiene comportamiento.**
   - `Comprobante`: reglas cruzadas y máquina de estados guiada por el CDR.
   - `Kardex`: saldo no negativo y orden cronológico.
   - `MigracionLegado`: pendiente → facturada.
5. **La regla de dependencias se verifica con pruebas** (`tests/integration/test_arquitectura.py`).

## Consecuencias

- Cambiar memoria → PostgreSQL, o la OSE simulada → la real, se hace en un solo archivo (`bootstrap.py`). Ya se hizo dos veces sin tocar el núcleo: SQLite ([ADR 0011](0011-persistencia-sqlite-como-segundo-adaptador.md)) y el envío real a SUNAT ([ADR 0012](0012-envio-real-a-sunat-y-validacion-contra-el-servicio-beta.md)).
- Las pruebas de dominio corren en milisegundos y sin HTTP.
- Hay más archivos que en un MVC plano: es el costo de poder sustituir adaptadores.
