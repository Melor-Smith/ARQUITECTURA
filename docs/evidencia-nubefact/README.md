# Evidencia: el OSE-DEMO de Nubefact aceptó el XML del sistema

El 12/11/2026 se probó el XML que genera el sistema en **<https://probar-xml.nubefact.com/>**. Esa herramienta envía el XML al **OSE-DEMO de Nubefact**, un Operador de Servicios Electrónicos autorizado por SUNAT, en modo de pruebas y sin validez legal. Antes de enviarlo, lo firma con su propio certificado de prueba.

## Resultado

| Comprobante | Qué se envió | Respuesta del OSE (CDR) |
|---|---|---|
| **20556677884-01-F46N-1** | Factura al contado de ABC (arroz y azúcar, S/ 359.90), generada con `python -m src.adapters.inbound.cli generar-xml` y la fecha del día | **`ResponseCode` 0: "La Factura Electrónica F46N-1 ha sido ACEPTADA"** |
| **20556677884-01-FDM6-1** | **El caso de estudio:** la motocicleta (valor 4 237.29 + IGV 762.71 = S/ 5 000.00), generada con el formulario `/venta` **sin firma** y enviada a las 18:50 | **`ResponseCode` 0: "La Factura Electrónica FDM6-1 ha sido ACEPTADA"** |

| Archivo | Qué es |
|---|---|
| [`20556677884-01-F46N-1.xml`](20556677884-01-F46N-1.xml) | El XML tal como lo generó el sistema (firmado por el sistema; la herramienta lo volvió a firmar) |
| [`R-20556677884-01-F46N-1.xml`](R-20556677884-01-F46N-1.xml) | El CDR (`ApplicationResponse`) que devolvió el OSE-DEMO |
| [`20556677884-01-FDM6-1.xml`](20556677884-01-FDM6-1.xml) | El XML **sin firma** de la motocicleta. Se **reconstruyó** con el caso de uso `GenerarXmlVenta` usando los mismos datos del formulario y la misma hora de emisión (18:50:26). El generador es determinista, así que es el mismo documento. En ese momento el formulario aún lo entregaba compacto, en una sola línea; hoy lo entrega indentado, con el mismo contenido |
| [`R-20556677884-01-FDM6-1.xml`](R-20556677884-01-FDM6-1.xml) | El CDR que devolvió el OSE-DEMO para la motocicleta |

**Cómo leer el CDR:**
- `cac:DocumentResponse/cac:Response/cbc:ResponseCode` = **0**: aceptado. Es el mismo código de aceptación de SUNAT.
- `cac:DocumentReference`: F46N-1, tipo 01, emitido el 12/11/2026 a las 09:54:33. Coincide con el XML enviado.
- `cac:IssuerParty` y `cac:RecipientParty`: emisor 20556677884 (ABC) y cliente 20123456786, los del XML.
- `cbc:StatusReasonCode` 0000 y 0001: el ambiente es DEMO y el documento no tiene validez legal.
- `cbc:DocumentHash`: es el resumen de la **firma de Nubefact**, no el de la firma del sistema, porque la herramienta vuelve a firmar el XML.

## Cómo repetir la prueba

1. Doble clic en [`iniciar.bat`](../../iniciar.bat) (o `python iniciar.py`): levanta el sistema y abre **`http://127.0.0.1:8000/venta`**.
2. Registrar la venta (viene cargada la motocicleta), dejar **sin marcar** "Incluir firma" y pulsar **Generar XML**.
3. Pulsar **Copiar XML**, pegarlo en probar-xml.nubefact.com, dejar el destino **OSE**, marcar **Firmar** y pulsar **Enviar**.
4. Guardar el XML, el CDR y la captura en esta carpeta.

## Cómo copiar el XML a la herramienta

Arrastre el archivo al panel "PEGA O ARRASTRA TU XML", o use el botón **Copiar XML** del formulario. Si lo copia a mano, ábralo como texto (Bloc de notas o VS Code). Después de pegarlo, pulse **Enviar** directamente, **sin pulsar *BeautifyXML***.

En XML, un `&` dentro de un texto se escribe `&amp;`. Por ejemplo, el cliente "BODEGA SAN MARTÍN & HIJOS" de [`factura-credito-F001-2.xml`](../ejemplos/factura-credito-F001-2.xml) y [`factura-isc-icbper-FA01-1.xml`](../ejemplos/factura-isc-icbper-FA01-1.xml) figura en el archivo como `SAN MARTÍN &amp; HIJOS`. Esos dos XML validan contra el XSD y SUNAT beta los aceptó ([evidencia](../evidencia-sunat/README.md)). Pero si el texto se reformatea o se copia desde una vista que decodifica el contenido, el `&amp;` se convierte en `&` suelto. Entonces la herramienta responde *"The entity name must immediately follow the '&' in the entity reference"*. Ese mensaje lo da el analizador de XML; no es una regla de SUNAT ni un rechazo del OSE.

## Respuestas del OSE que no son errores del XML

| Código | Mensaje | Causa | Qué hacer |
|---|---|---|---|
| **1033** | "El comprobante fue registrado previamente con otros datos" | El OSE-DEMO es **compartido**: otra persona ya envió ese RUC, tipo, serie y número | Usar una serie nueva. El formulario propone una distinta en cada visita |
| **1083** | "El número de RUC del receptor no existe" | El OSE verifica el RUC del cliente contra el padrón de SUNAT. Un RUC inventado no pasa aunque su dígito verificador sea válido | Usar un RUC que exista. El formulario trae uno que el OSE ya aceptó |
| *The entity name must immediately follow the '&'…* | Error del analizador de XML, antes de cualquier regla | Llegó un `&` suelto: el `&amp;` del archivo se perdió al copiar o reformatear | Copiar como se indica arriba |

Ninguno de estos rechazos se debe a la estructura UBL ni a los cálculos:
- el 1033 y el 1083 son validaciones contra el registro del OSE o de SUNAT, que el sistema no puede hacer sin conectarse a ellos;
- el error del `&` ocurre al copiar el texto, antes de que el OSE lo revise.
