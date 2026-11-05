# ADR 0007: Libros electrónicos PLE 14.1 y 12.1 a partir del dominio

- **Estado:** aceptado.
- **Observación que atiende:** 10. No había 14.1 ni 12.1, y el "Kardex valorizado" que se mencionaba es el 13.1.

## Decisión

1. **El formato 14.1 (Registro de Ventas)** se construye a partir de los comprobantes con validez tributaria del periodo:
   - las notas de crédito se anotan en negativo;
   - las operaciones en USD se convierten a soles con el tipo de cambio;
   - las notas llevan los datos del comprobante modificado.
2. **El formato 12.1 (Inventario permanente en unidades físicas)** se construye a partir del `Kardex`. Es el que corresponde a la ficha antigua, que solo tiene cantidades. El 13.1 valorizado queda fuera de alcance porque requiere costos.
3. **La ficha antigua se completa al migrarla:**
   - glosa → producto, mediante la tabla de homologación y un factor de conversión de unidades;
   - tipo de existencia (tabla 5);
   - tipo de operación (tabla 12);
   - documento de soporte (tabla 10, tipo 00);
   - establecimiento;
   - saldo.
4. **Equivalencia de unidades.** El XML usa el Catálogo 03 (UNECE) y se creó la equivalencia a la tabla 6 numérica (`UnidadMedida.unidad_ple`). *Actualización (05/11/2026): el validador PLE 5.2.0.7 rechazó esos códigos numéricos en el campo 16 y aceptó los UN/ECE; el 12.1 usa UN/ECE ([evidencia](../../docs/evidencia-ple/README.md)). La equivalencia se conserva solo como referencia.*
5. **Separación modelo/vista.** Las filas tipadas viven en el dominio (`libros.py`). *Reemplazado por el [ADR 0010](0010-estructura-ple-en-el-dominio-validada-contra-el-anexo-2.md): la estructura del TXT también es del dominio y se valida contra el Anexo 2 oficial.*

## Consecuencias

- `GET /api/v1/libros-electronicos/registro-ventas/{AAAAMM}` y `GET /api/v1/libros-electronicos/inventario-unidades-fisicas/{AAAAMM}` entregan el TXT con su nombre oficial, o la vista JSON.
- Antes de presentar los libros hay que validar el TXT con el programa PLE vigente (ver `specs/ple/`).
