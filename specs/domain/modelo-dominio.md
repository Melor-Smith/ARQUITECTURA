# Modelo de dominio

El código vive en [`src/domain/`](../../src/domain): Python puro, sin frameworks. El diagrama de clases y la máquina de estados están en [`arquitectura.md`](../architecture/arquitectura.md) §5 y §6.

## Objetos de valor ([`valores.py`](../../src/domain/valores.py))

| Objeto | Invariante | Error |
|---|---|---|
| `Ruc` | 11 dígitos, prefijo 10/15/16/17/20 y dígito verificador módulo 11 (pesos 5,4,3,2,7,6,5,4,3,2) | 422 `ERR-SUNAT-RUC` |
| `DocumentoIdentidad` | Según el Catálogo 06: DNI 8 dígitos; CE y pasaporte hasta 12 caracteres; RUC → `Ruc` | 422 `ERR-SUNAT-DOC-IDENTIDAD` |
| `Serie` | `^[FB][A-Z0-9]{3}$` | 422 `ERR-SUNAT-SERIE` |
| `Correlativo` | `int` de 1 a 99 999 999 | 422 `ERR-SUNAT-CORRELATIVO` |
| `NumeroComprobante` | `Serie` + `Correlativo`; se serializa como `F001-1` y al parsear acepta ceros a la izquierda | — |
| `ConfiguracionISC` | 01 ⇒ tasa; 02 ⇒ monto fijo; 03 ⇒ tasa y precio de venta al público; sin combinaciones contradictorias | 422 `ERR-SUNAT-CAT08` |

## Agregado `Comprobante` ([`comprobante.py`](../../src/domain/comprobante.py))

### Cálculo de cada línea (`Linea.calcular`)

Todo el cálculo usa `Decimal`, redondeando cada monto a 2 decimales con mitad hacia arriba.

```
valor_venta = cantidad × valor_unitario
ISC         = 01: valor_venta × tasa
              02: cantidad × monto_fijo
              03: (cantidad × precio_venta_publico × 0.847) × tasa
base_IGV    = valor_venta + ISC                  (solo afectación 10)
IGV         = base_IGV × 0.18                    (afectaciones 20, 30 y 40 → 0)
ICBPER      = cantidad × tasa_icbper(año)        (0.10 en 2019 … 0.50 desde 2023; unidad NIU)
```

### Totales (`Totales.de_lineas`)

- `gravadas`, `exoneradas`, `inafectas` y `exportacion` suman el valor de venta según la afectación de cada línea.
- `importe_total` = valor de venta + ISC + IGV + ICBPER.

### Reglas cruzadas (`BorradorComprobante.preparar`)

| Regla | Error |
|---|---|
| Factura (01) ⇒ serie que empieza con F | `ERR-SUNAT-SERIE` |
| Factura (01) ⇒ cliente con RUC, salvo exportación | `ERR-SUNAT-RUC` |
| Boleta (03) ⇒ serie que empieza con B | `ERR-SUNAT-SERIE` |
| Boleta mayor a S/ 700 ⇒ cliente identificado | `ERR-SUNAT-COMPROBANTE` |
| USD ⇒ `tipo_cambio` mayor a 0; PEN ⇒ sin tipo de cambio | `ERR-SUNAT-COMPROBANTE` |
| Fecha no futura y dentro del plazo de envío (configurable; 3 días) | `ERR-SUNAT-FECHA` |
| Notas (07 y 08) ⇒ referencia existente y no rechazada, motivo (Catálogo 09 o 10), sustento, la misma letra de serie, el mismo cliente y la misma moneda | `ERR-SUNAT-COMPROBANTE` / `ERR-REFERENCIA-NO-EXISTE` |
| Nota de crédito ⇒ no puede exceder el saldo no acreditado del comprobante | `ERR-SUNAT-COMPROBANTE` |
| Línea con producto ⇒ el producto existe y la unidad es su unidad de inventario | `ERR-PRODUCTO-NO-EXISTE` / `ERR-SUNAT-CAT03` |

### Estados

La máquina de estados está en `arquitectura.md` §5.

- **El estado sale del CDR:**
  - código 0 → aceptado;
  - de 2000 a 3999 → rechazado;
  - 4000 o más, o código 0 con observaciones → aceptado con observaciones;
  - de 100 a 1999 son excepciones: no hay CDR.
- **Un comprobante con CDR no se reenvía** (`ConflictoDominio` → 409).

## Forma de pago e importe en letras ([`pagos.py`](../../src/domain/pagos.py), [`letras.py`](../../src/domain/letras.py))

| Elemento | Regla | Error |
|---|---|---|
| `FormaPago` | Solo en facturas (contado por defecto). Al crédito: entre 1 y 60 cuotas, montos mayores a 0, vencimientos posteriores a la emisión y crecientes, y la suma de las cuotas igual al importe total | 422 `ERR-SUNAT-FORMA-PAGO` |
| `importe_en_letras` | Leyenda 1000: `TRESCIENTOS CINCUENTA Y NUEVE CON 90/100 SOLES`, con apócopes (UN MIL, VEINTIÚN MILLONES) | — |

## Inventario ([`inventario.py`](../../src/domain/inventario.py))

| Elemento | Regla |
|---|---|
| `Kardex` | Saldo = Σ entradas − Σ salidas; **nunca negativo**; los movimientos van en **orden cronológico**; el tipo de operación (tabla 12) debe admitir el sentido del movimiento |
| `FichaLegado` | Exactamente uno de `ingreso` o `salida` mayor a 0 (`ERR-LEGADO-SIN-MOVIMIENTO`, `ERR-LEGADO-AMBIGUA`) |
| `Homologacion` | Glosa normalizada (sin tildes ni mayúsculas) → producto y `factor_conversion` |
| `DocumentoSoporte` / `clasificar_documento_legado` | El `nro_documento` se clasifica por lo que es: vale interno (00), factura (01) o boleta (03), física o electrónica, o guía de remisión (09). Lo que no se reconoce, o no tiene documento, se registra como 00 **con observación**. Nunca se convierte en un número SUNAT nuevo |
| `parsear_fecha_legado` | Acepta AAAA-MM-DD, DD/MM/AAAA, DD-MM-AAAA, DD.MM.AAAA y DD/MM/AA; una fecha imposible es `ERR-LEGADO-FECHA` |
| `MigracionLegado` | Las salidas por venta respaldadas por vale o guía quedan `PENDIENTE_FACTURACION`, pasan a `FACTURADA` al emitirse el comprobante y vuelven a pendiente si la OSE lo rechaza. Si ya tenían factura o boleta en el sistema antiguo quedan `FACTURADA_EN_SISTEMA_ANTIGUO`. Los demás movimientos quedan `NO_REQUIERE_FACTURA` |

## Libros ([`libros.py`](../../src/domain/libros.py))

`FilaRegistroVentas141` y `FilaInventario121` están documentadas campo por campo en [`specs/ple/`](../ple). Su estructura en el TXT (número, tipo, longitud y obligatoriedad de cada campo, según el Anexo 2) es `ESTRUCTURA_141` y `ESTRUCTURA_121` en `src/domain/ple_estructura.py`, contrastada con el Excel oficial ([ADR 0010](../adr/0010-estructura-ple-en-el-dominio-validada-contra-el-anexo-2.md)).
