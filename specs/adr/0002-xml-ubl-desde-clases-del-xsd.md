# ADR 0002: XML UBL 2.1 desde clases derivadas del XSD, validado y firmado

- **Estado:** aceptado.
- **Observaciones que atiende:** 3, 3a a 3d y 6.

## Contexto

El XML se armaba concatenando f-strings, y además había una plantilla en `specs/templates`. El resultado tenía tres defectos verificados:
- un `&` generaba XML mal formado;
- faltaba `cbc:InvoiceTypeCode`;
- en la línea, `cac:TaxTotal` iba después de `cac:Item`, cuando el XSD exige lo contrario.

El XSD incluido no servía para validar (le faltaba `common/`), no había firma, y el "hash CPE" era un SHA-256 del XML sin firmar.

## Decisión

1. **XSD oficiales completos.** Se versionan los 16 archivos de OASIS UBL 2.1 (maindoc Invoice, CreditNote y DebitNote, más `common/`) en `specs/contracts/ubl-2.1/xsd`.
2. **Clases generadas con `xsdata`** (`scripts/generar_clases_ubl.*`) en `src/adapters/outbound/ubl/generated`. El generador (`generador.py`) solo instancia esas clases, de modo que:
   - el serializador escapa los caracteres especiales;
   - el orden de los elementos sale del XSD;
   - un elemento inexistente ni siquiera se puede construir.
3. **Validación con `lxml`** contra el XSD **antes** de firmar (contenido de negocio) y **después** (documento completo, incluida `ds:Signature`). Un fallo es un defecto interno (500), nunca culpa del cliente.
4. **Firma XMLDSig enveloped con `signxml`** (RSA-SHA256, C14N 1.0) en `ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent`, con `Id="SignatureSP"` referenciado desde `cac:Signature`. El **hash CPE es el `ds:DigestValue`**.
5. **Parser endurecido contra XXE** (`resolve_entities=False`, `no_network=True`).
6. **Se eliminó la plantilla.** `docs/ejemplos/` contiene salidas reales generadas por el sistema.
7. **CI regenera las clases** y falla si difieren de las versionadas.

## Consecuencias

- El código generado ocupa unos 3 MB. Es estable y no se edita a mano, y el lint lo excluye.
- El XML tiene un formato predecible. La OSE simulada demuestra que cualquier alteración posterior a la firma se detecta (CDR 2335).
- En producción se reemplaza el certificado autofirmado de desarrollo por el `.pfx` del emisor (`ABC_CERTIFICADO_PFX`), que nunca se versiona.
