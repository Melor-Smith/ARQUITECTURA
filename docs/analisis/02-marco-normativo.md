# 2. Marco normativo y estándar UBL

## 2.1 Normas y dónde se cumplen en el código

| Norma | Qué exige al sistema | Dónde se implementa |
|---|---|---|
| **RS 097-2012/SUNAT** y modificatorias (SEE desde los sistemas del contribuyente) | Comprobantes electrónicos en UBL 2.1, firmados digitalmente y enviados a SUNAT o a una OSE | `adapters/outbound/ubl`, `firma`, `ose`; caso de uso `EmitirComprobante` |
| Anexo 8 de la RS 097-2012 (**catálogos**) | Códigos de documento (01), moneda (02), unidad (03), tributo (05), documento de identidad (06), afectación (07), **ISC (08)**, motivos de nota (09 y 10), documentos relacionados (12), tipo de precio (16), leyendas (52) y tipo de operación (51) | `src/domain/catalogos.py`; mapeo en la [matriz](../../specs/traceability/matriz-trazabilidad.md) |
| **RS 193-2020/SUNAT** | Informar la forma de pago (Contado o Crédito) y las cuotas en la factura | `src/domain/pagos.py`; `cac:PaymentTerms` |
| **Ley 30884** | ICBPER por bolsa plástica, con tasa según el año | `tasa_icbper` en `tributos.py` |
| **TUO de la Ley del IGV e ISC** | IGV 18 % sobre (valor de venta + ISC); ISC por sistema al valor, monto fijo o precio de venta al público (× 0,847) | `Linea.calcular`, `ConfiguracionISC` |
| **RS 234-2006/SUNAT** | Registro de ventas y registro de inventario permanente según los ingresos | `Kardex`, `inventario_121`, `registro_ventas_141` |
| **RS 286-2009/SUNAT** (PLE) | Estructura de los libros 14.1 y 12.1 (Anexo 2, PLE 5.0), tablas 2, 4, 5, 6, 10, 12 y 13, y nombre del archivo | `src/domain/libros.py`, `src/domain/ple_estructura.py`; [`specs/ple/`](../../specs/ple), con el Excel oficial en `specs/ple/anexo2/` |
| **OASIS UBL 2.1** | Estructura XML y orden de los elementos | XSD oficiales en `specs/contracts/ubl-2.1/xsd`; clases generadas con xsdata |

## 2.2 Estudio del XSD `UBL-Invoice-2.1.xsd`

En lugar de describir el XSD de memoria, el proyecto lo **procesa**:

1. **Generación de clases.** `xsdata` convierte `UBL-Invoice-2.1.xsd` y sus 13 XSD de `common/` en dataclasses Python. Así se ve qué elementos existen y en qué orden van.
2. **Cardinalidad.** `scripts/matriz.py` recorre el XSD elemento por elemento para cada dato de la matriz y calcula su cardinalidad, siguiendo también la herencia de tipos para los atributos.
3. **Hallazgo principal.** De los 64 datos de la matriz que viajan en el XML, **36 son exigidos por SUNAT pero opcionales en el XSD de OASIS**. Ejemplos: `cbc:InvoiceTypeCode` es `0..1`, `@unitCode` es opcional y `cac:Party` es `0..1`. Esa diferencia es el "perfil SUNAT". **Validar contra el XSD es necesario, pero no suficiente.** Por eso las reglas de SUNAT viven en el dominio, y las pruebas de generación verifican que esos datos opcionales del XSD siempre estén presentes.
4. **Firma.** `ext:ExtensionContent` admite cualquier elemento (`xsd:any`). La firma `ds:Signature` va ahí y se valida contra el esquema XMLDSig que importa UBL.

## 2.3 Punto clave: el Catálogo 08 (sistemas de cálculo del ISC)

| Código | Sistema | Dato que envía el cliente | Cálculo en el dominio | XML |
|---|---|---|---|---|
| 01 | Al valor | `tasa` | valor de venta × tasa | `cbc:TierRange`=01, `cbc:Percent` |
| 02 | Aplicación del monto fijo | `monto_fijo` | cantidad × monto fijo | `cbc:TierRange`=02, `cbc:PerUnitAmount` |
| 03 | Precios de venta al público | `tasa` y `precio_venta_publico` | cantidad × precio × 0,847 × tasa | `cbc:TierRange`=03, `cbc:Percent` |

En los tres casos, el IGV se calcula sobre (valor de venta + ISC). Las configuraciones incompletas o contradictorias se rechazan con 422 `ERR-SUNAT-CAT08`; un código fuera del catálogo, con 400.

## 2.4 Fuentes y nivel de confianza

| Tema | Fuente | Confianza |
|---|---|---|
| Estructura XML | XSD oficiales de OASIS UBL 2.1, incluidos en el repositorio y usados por las pruebas | Alta: verificado automáticamente |
| Catálogos y reglas SUNAT | Anexo 8 de la RS 097-2012 y guías de elaboración de XML de SUNAT | Media-alta: hay que contrastarlo con la versión vigente del portal de SUNAT antes de producción |
| Estructura de los TXT del PLE | Excel oficial del Anexo 2 de la RS 286-2009 (PLE 5.0), versionado en `specs/ple/anexo2/` | Alta para la estructura: cada campo se verifica automáticamente contra el Excel oficial (ADR 0010). Pendiente: cargar los TXT en el programa PLE de escritorio |
| Tasas (IGV, ICBPER) | TUO de la Ley del IGV e ISC; Ley 30884 | Alta para las tasas vigentes; se parametrizan en un único módulo |

## 2.5 Criterios de verificación

- **Lo verificable se verificó con código:**
  - la validación de cada XML contra los XSD oficiales;
  - el cálculo de cardinalidades desde esos XSD;
  - la evaluación de cada XPath de la matriz contra XML generados;
  - el contraste de la estructura de los TXT del PLE con el Excel oficial del Anexo 2.
- **Lo normativo** (catálogos, tasas, estructura del PLE) **se declara con su fuente y su nivel de confianza** en la sección 2.4. Antes de usarlo en producción, debe contrastarse con la versión vigente publicada por SUNAT.
- **Las decisiones de diseño** están registradas en los ADR, con su justificación, para que se puedan discutir.
