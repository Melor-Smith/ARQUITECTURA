# ADR 0011: Persistencia SQLite como segundo adaptador de los mismos puertos

- **Estado:** aceptado (2026-11-05).
- **Complementa:** ADR 0001 (hexagonal) y ADR 0004 (correlativo atómico).

## Contexto

Todos los puertos de persistencia tenían un único adaptador, en memoria. La arquitectura prometía que "cambiar la memoria por una base de datos se hace solo en `bootstrap.py`", pero nada lo demostraba. Además había tres riesgos:

- **Datos volátiles.** Al reiniciar el servidor se perdían los comprobantes, el Kardex y el correlativo. Eso incumple el atributo de calidad AC-12 (conservación de XML y CDR).
- **Sin rollback.** La unidad de trabajo en memoria solo bloqueaba con un `RLock`. Una falla a mitad de un caso de uso podía dejar un agregado modificado.
- **Lotes de migración.** Una ficha que fallaba dentro de un lote no tenía cómo deshacer solo su parte.

## Decisión

1. **Adaptador SQLite** (`src/adapters/outbound/persistencia/sqlite.py`): implementa los mismos 9 puertos que el de memoria. Usa la librería estándar, sin dependencias nuevas.
2. **Transacciones reales:**
   - `BEGIN IMMEDIATE` en la transacción externa;
   - `SAVEPOINT` en las anidadas: en un lote, una ficha que falla se deshace sola y las demás se conservan;
   - `ROLLBACK` ante cualquier excepción.
3. **Correlativo atómico**, como pedía el ADR 0004:
   - `INSERT … ON CONFLICT DO UPDATE SET ultimo = ultimo + 1 RETURNING ultimo`, dentro de la transacción de emisión;
   - una emisión rechazada no consume número;
   - la clave primaria `(tipo, serie_numero)` impide duplicados aunque el código fallara.
4. **Agregados como documentos JSON con columnas de búsqueda.** El codec (`codec.py`) usa los *type hints* de las dataclasses del dominio:
   - **no se usa `pickle`**, que ejecutaría código si la base de datos fuera alterada;
   - no hay un mapeo manual por clase que pueda divergir del modelo;
   - `Decimal` se guarda como texto, sin pérdida;
   - las uniones ambiguas se etiquetan (los catálogos 09 y 10 comparten el código `01`);
   - al leer, los `__post_init__` del dominio vuelven a validar los datos.
5. **Selección por configuración**, sin tocar el código:
   - `ABC_BASE_DATOS=/ruta/abc.db` usa SQLite; sin esa variable, memoria;
   - la imagen Docker usa SQLite en el volumen `/datos` por defecto.
6. **La prueba del hexágono.** La fixture `contenedor` de `tests/conftest.py` está parametrizada con `memoria` y `sqlite`. Todas las pruebas de API, contrato, PLE y rendimiento corren **contra los dos adaptadores** y deben dar el mismo resultado.

## Consecuencias

- La API, los casos de uso y el dominio no cambiaron en una sola línea para soportar SQLite. El intercambio de adaptadores queda demostrado, no solo prometido.
- `tests/integration/test_persistencia_sqlite.py` verifica:
  - que los datos sobreviven a un reinicio y el correlativo continúa;
  - el rollback de una emisión fallida;
  - el `SAVEPOINT` en los lotes;
  - que la base impide duplicados;
  - correlativos únicos con 12 hilos concurrentes;
  - que los importes no pierden precisión.
- **Límites:**
  - SQLite admite un solo escritor a la vez; basta para una distribuidora con un servidor, y el `RLock` serializa las escrituras de ese proceso;
  - para varios servidores contra la misma base, se implementan los mismos puertos sobre PostgreSQL, con el mismo SQL de correlativo (`… RETURNING`) y la misma restricción `UNIQUE`;
  - el esquema se crea con `CREATE TABLE IF NOT EXISTS`. Cuando haya cambios de esquema en producción, se adoptará una herramienta de migraciones como Alembic.
