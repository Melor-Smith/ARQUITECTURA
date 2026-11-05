# ADR 0004: Serie y correlativo como objetos de valor; correlativo asignado de forma atómica

- **Estado:** aceptado.
- **Observaciones que atiende:** 1, 4 y 7a, y el `len(DB)+1` de la migración.

## Decisión

1. `Serie` (`^[FB][A-Z0-9]{3}$`), `Correlativo` (`int`, de 1 a 99 999 999) y `NumeroComprobante` son objetos de valor inmutables. Se unen solo al serializar `cbc:ID` (`F001-1`). Al consultar se aceptan ceros a la izquierda.
2. **El correlativo lo asigna el servidor**, mediante el puerto `SecuenciaCorrelativos`, por (RUC, tipo, serie). Si el cliente lo envía, la respuesta es 400.
3. **Reglas cruzadas:** 01 ⇒ serie F y cliente con RUC; 03 ⇒ serie B; en las notas, la letra de la serie debe ser la del comprobante modificado.
4. **El correlativo se reserva después de validar todas las reglas**, para que un 422 no deje huecos.
5. **Duplicados:** el repositorio rechaza un número repetido (409). Para los reintentos de red, el cliente envía `Idempotency-Key`:
   - misma clave y mismo contenido → 200 con el comprobante original;
   - misma clave y otro contenido → 409.
6. Para continuar una serie ya usada en otro sistema, `construir_contenedor(ultimos_correlativos=...)` define el último número emitido.

## Implementación en producción

```sql
CREATE TABLE serie (
    ruc char(11), tipo char(2), serie char(4), ultimo int NOT NULL,
    PRIMARY KEY (ruc, tipo, serie)
);
UPDATE serie SET ultimo = ultimo + 1
 WHERE ruc = $1 AND tipo = $2 AND serie = $3
RETURNING ultimo;
-- y en la tabla comprobante: UNIQUE (ruc, tipo, serie, correlativo)
```

## Consecuencias

`tests/integration/test_concurrencia.py` lo prueba: 200 reservas concurrentes producen exactamente 1..200, y 20 emisiones HTTP simultáneas producen B001-1..B001-20 sin sobrescrituras.
