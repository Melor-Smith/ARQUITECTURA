# Evidencia de la cuenta DEMO de Nubefact

> **Estado: pendiente.** Esta carpeta guarda las capturas del guion de la [§3.5 de los casos de uso](../03-casos-de-uso.md#35-descubrimiento-con-usuarios-lo-que-falta-hacer).

## Cómo registrar cada paso

1. **Nombre de la captura:** `NN-paso.png`. Por ejemplo, `01-factura-credito-dos-cuotas.png` o `03-rechazo-ruc-invalido.png`.
2. **Antes de capturar,** oculte cualquier dato personal o credencial de la cuenta.
3. **Una fila por hallazgo** en la tabla de abajo. Cada hallazgo confirma o refuta una hipótesis (H1-H5) o compara un campo con nuestro contrato.

| Paso del guion | Captura | Qué se observó | Confirma / refuta | Consecuencia para ABC |
|---|---|---|---|---|
| 1. Factura al crédito con dos cuotas | | | Compara con `forma-pago.schema.json` | |
| 2. Boleta mayor a S/ 700 sin DNI | | | Compara con `ERR-SUNAT-COMPROBANTE` | |
| 3. Rechazo por RUC inválido | | | Compara con nuestro `problem+json` | |
| 4. OSE sin respuesta | | | H4 | |
| 5. XML descargado, validado con `ValidadorXsdLxml` | | | — | |
| 6. Anulación de una factura (comunicación de baja) | | | H5 · compara con el ADR 0014 | |
