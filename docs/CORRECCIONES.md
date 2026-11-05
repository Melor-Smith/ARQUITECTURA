# Respuesta a la revisión (38/100): observación → corrección → evidencia

Cada fila indica qué se corrigió y **dónde comprobarlo**: un archivo del código y una prueba automática que falla si la corrección se pierde. Para reproducir todo: `pytest -q` (484 pruebas).

Convención de rutas: `tests/acceptance/test_api_comprobantes.py::TestSerieYCorrelativo` significa la clase de pruebas `TestSerieYCorrelativo` dentro de ese archivo.

---

## 1. Modelo de dominio y DTOs

| # | Observación | Corrección | Evidencia |
|---|---|---|---|
| 1.1 | La serie solo aceptaba `F` (boleta `B001` → 400). | La serie es un objeto de valor con el patrón `^[FB][A-Z0-9]{3}$`. Regla cruzada: 01 ⇒ serie F y cliente con RUC; 03 ⇒ serie B. | [`src/domain/valores.py`](../src/domain/valores.py) `Serie`; [`src/domain/comprobante.py`](../src/domain/comprobante.py) `_validar_venta`; `test_api_comprobantes.py::TestSerieYCorrelativo::test_boleta_b001_es_aceptada` |
| 1.2 | Exigía exactamente 6 dígitos; el correlativo legal de 8 dígitos daba 400. | `Correlativo` es un `int` entre 1 y 99 999 999. Serie y correlativo solo se unen al serializar (`cbc:ID`). | `Correlativo`, `NumeroComprobante` en `valores.py`; `test_correlativo_legal_de_8_digitos` (emite `F001-12345678`) |
| 1.3 | La serie solo podía ser numérica (`FA01` era imposible). | El patrón es alfanumérico. | `test_serie_alfanumerica_fa01`; `tests/unit/test_valores.py::TestSerie` |
| 1.4 | El OpenAPI decía `\d{1,8}` y el código `\d{6}`. | El OpenAPI ya no se escribe a mano: se **genera desde el código**, y una prueba compara el YAML versionado con el generado. | [`specs/contracts/openapi.yaml`](../specs/contracts/openapi.yaml); `tests/acceptance/test_contrato.py::test_el_openapi_versionado_coincide_con_el_generado_por_el_codigo` |
| 1.5 | El correlativo lo enviaba el cliente; la migración lo calculaba como `len(DB)+1`, que no es atómico. | El servidor lo **asigna** con una secuencia bajo bloqueo, por tipo y serie. Enviar `correlativo` → 400. Un rechazo de negocio no consume número. | [`memoria.py`](../src/adapters/outbound/persistencia/memoria.py) `SecuenciaCorrelativosEnMemoria`; `tests/integration/test_concurrencia.py` (200 hilos → 1..200 sin repetir); `test_rechazo_de_negocio_no_consume_correlativo` |
| 2 | `ItemFactura` no tenía unidad de medida; el XML siempre decía `unitCode='NIU'`. | `unidad_medida` es obligatoria y sale del Catálogo 03 (UNECE Rec. 20: NIU, ZZ, KGM, LTR, BX…). Va en `unitCode` de cada línea. El producto tiene su unidad de inventario y se valida la coherencia. | `UnidadMedida` en [`catalogos.py`](../src/domain/catalogos.py); `TestUnidadesUnece::test_saco_de_50_kg_facturado_en_kgm` |
| 3 | XML armado con plantilla y concatenación de f-strings. | Se eliminó la plantilla. El XML se construye con **clases generadas por `xsdata`** desde los XSD oficiales completos de UBL 2.1 (maindoc + `common/`). | [`src/adapters/outbound/ubl/generador.py`](../src/adapters/outbound/ubl/generador.py); [`generated/`](../src/adapters/outbound/ubl/generated); [`specs/contracts/ubl-2.1/xsd`](../specs/contracts/ubl-2.1/xsd) |
| 3a | `&` producía XML mal formado. | El serializador escapa caracteres. | `tests/unit/generacion_xml/test_conformidad_y_regresion.py::test_cualquier_texto_del_usuario_produce_xml_valido`; `TestXml::test_descripcion_con_ampersand_genera_xml_bien_formado` |
| 3b | Faltaba `cbc:InvoiceTypeCode`. | Se emite con `listID` del Catálogo 51 (`0101`). | `test_invoice_type_code_catalogo_01_y_tipo_de_operacion_catalogo_51` |
| 3c | En la línea, `cac:TaxTotal` iba después de `cac:Item` y `cac:Price`. | El orden lo impone el XSD a través de las clases. | `test_orden_de_elementos_de_la_linea_segun_el_xsd` |
| 3d | El XSD incluido no servía (le faltaba `common/`) y nunca se usaba. | Se incluyeron los 16 XSD oficiales. El XML se valida con lxml **antes y después de firmar**, para factura, boleta, nota de crédito y nota de débito. | [`validador.py`](../src/adapters/outbound/ubl/validador.py); `test_cada_escenario_valida_contra_el_xsd_oficial[...]` (antes de firmar) y `test_valida_contra_el_xsd_oficial_completo_despues_de_firmar[...]` |
| 4 | El payload de ejemplo de `specs/` era rechazado (`serie_numero` contra `serie_correlativo`). | Hay un solo contrato. Todos los ejemplos de [`specs/ejemplos`](../specs/ejemplos) alimentan el OpenAPI **y** se prueban contra la API. | `test_contrato.py::test_todos_los_ejemplos_del_contrato_son_aceptados` |
| 5 | El cliente enviaba `igv_item` y los totales; con `importe_total=1` e IGV 999 la respuesta era 201. Importes en `float`. | El cliente envía solo cantidad, valor unitario, afectación y la configuración del ISC. El **dominio calcula** ISC (sistemas 01, 02 y 03), IGV, ICBPER y totales con `Decimal`. Los campos de impuestos están prohibidos en el contrato. | [`src/domain/tributos.py`](../src/domain/tributos.py), `Linea.calcular`, `Totales.de_lineas`; `TestCalculoDelegadoAlCliente`; `tests/unit/test_tributos.py` |
| 9d | El RUC solo aceptaba los prefijos 10 y 20 y no verificaba el dígito de control. | Prefijos 10, 15, 16, 17 y 20, más **módulo 11**. `20123456780` → 422 `ERR-SUNAT-RUC`. | `Ruc` en `valores.py`; `TestRuc::test_rechaza_el_ruc_con_digito_verificador_incorrecto_que_el_sistema_anterior_aceptaba`; `test_prefijos_15_16_17_aceptados` |

## 2. Arquitectura MVC → Hexagonal

| # | Observación | Corrección | Evidencia |
|---|---|---|---|
| 6 | `estado_sunat = "ACEPTADO"` estaba fijo, sin firma, CDR ni envío. El "hash CPE" era un SHA-256 del XML sin firmar. | Firma XMLDSig (signxml) dentro de `ext:UBLExtensions`. El hash CPE es el `ds:DigestValue`. El estado sale del **CDR**. La OSE simulada verifica la firma y el XSD, y detecta un XML alterado (código 2335). | [`xmldsig.py`](../src/adapters/outbound/firma/xmldsig.py), [`ose/simulada.py`](../src/adapters/outbound/ose/simulada.py), `Comprobante.registrar_cdr`; `test_firma_xmldsig_en_ubl_extensions_y_hash_cpe_es_el_digest_value`; `test_la_ose_simulada_acepta_y_detecta_un_xml_alterado_despues_de_firmar` |
| 8a | El código de producción importaba de `tests/mocks`. | Los datos maestros viven en el adaptador de persistencia ([`semillas.py`](../src/adapters/outbound/persistencia/semillas.py)) y se inyectan. | `tests/integration/test_arquitectura.py::test_ningun_modulo_de_produccion_importa_desde_tests` |
| 8b | Métodos estáticos y dependencia del repositorio concreto; no había interfaces. | Puertos como `Protocol` en [`src/application/puertos.py`](../src/application/puertos.py). Los casos de uso reciben todo por constructor y [`src/bootstrap.py`](../src/bootstrap.py) es la única raíz de composición. | `test_los_puertos_son_interfaces`; `test_los_casos_de_uso_reciben_sus_dependencias_por_constructor` |
| 8c | El "Modelo" eran DTOs de Pydantic, sin entidades con comportamiento. | El dominio es Python puro: el agregado `Comprobante` (reglas cruzadas y máquina de estados), `Kardex` (saldo, sin saldo negativo, orden cronológico) y `MigracionLegado`. Pydantic vive solo en el adaptador HTTP. | `test_el_nucleo_no_depende_de_frameworks_ni_de_adaptadores[domain]` / `[application]` |
| 8d | La "Vista" se declaraba como el YAML de OpenAPI. | La Vista son las representaciones: JSON, XML firmado y TXT del PLE ([`vistas/`](../src/adapters/inbound/http/vistas)). El YAML es el **contrato** que las describe. | [`specs/architecture/arquitectura.md`](../specs/architecture/arquitectura.md) §2 |
| 8e | Los puertos del diagrama no existían en el código. | `GeneradorUBL`, `FirmaDigital`, `ClienteOSE`, `RepositorioKardex` y los demás existen, cada uno con su adaptador. El diagrama se dibujó **desde** el código. | `puertos.py`; `arquitectura.md` §3 |

## 3. Contratos API (OpenAPI)

| # | Observación | Corrección | Evidencia |
|---|---|---|---|
| 7a | Emitir dos veces `F001-000001` devolvía 201 y sobrescribía. | El número lo asigna el servidor, así que no hay colisiones. El repositorio rechaza duplicados (409). Con `Idempotency-Key`, la misma clave y el mismo contenido devuelven 200 con el comprobante original; la misma clave con otro contenido devuelve **409**. | `TestIdempotencia`; `test_dos_emisiones_no_se_sobrescriben` |
| 7b | Errores de formato y de negocio mezclados en 400. | **400** = no cumple el esquema. **422** = cumple el esquema pero viola una regla. | [`problemas.py`](../src/adapters/inbound/http/problemas.py); p. ej. `test_catalogo_08_codigo_inexistente` (400) frente a `test_catalogo_08_configuracion_incompleta` (422) |
| 7c | No había 401, 403 ni 5xx. | Bearer con alcances: 401 con `WWW-Authenticate` y 403. Si la OSE no responde: **202** `PENDIENTE_ENVIO`; en el reenvío, **503** con `Retry-After` o **502**. Ya aceptado → 409. | `TestSeguridad`; `TestOse` |
| 7d | El 201 prometía "aceptado por SUNAT" sin consultarla. | El 201 significa que la OSE devolvió CDR. El estado (`ACEPTADO`, `ACEPTADO_CON_OBSERVACIONES` o `RECHAZADO`) sale del CDR; un rechazo también revierte el Kardex. | `test_rechazo_de_la_ose_se_refleja_y_revierte_el_kardex` |
| — | Un solo formato de error. | `application/problem+json` (RFC 9457) en todas las respuestas 4xx y 5xx, con un `codigo` estable. | `test_errores_documentados_como_problem_json` |
| — | Solo cubría factura, sin boleta ni notas. | Factura (01), boleta (03), nota de crédito (07, Catálogo 09) y nota de débito (08, Catálogo 10), con unión discriminada por `tipo_comprobante`. | `TestNotas`; `test_cada_escenario_valida_contra_el_xsd_oficial[nota-credito]` / `[nota-debito]` |

## 4. Matriz de trazabilidad y normativa

| # | Observación | Corrección | Evidencia |
|---|---|---|---|
| 9a | El Catálogo 07 estaba mapeado a `TaxScheme/cbc:ID`. | Ahora se mapea a `cac:TaxCategory/cbc:TaxExemptionReasonCode`, que es lo que hace el código. | [`matriz-trazabilidad.md`](../specs/traceability/matriz-trazabilidad.md); `test_unidad_de_medida_catalogo_03_por_linea` y `test_igv_gravado_categoria_s_18_por_ciento_y_afectacion_10` |
| 9b | El `nro_documento` del sistema antiguo se mapeaba a `cbc:ID` y se le "sugería" un correlativo F001. | Se mapea al **documento de soporte** del Kardex (tabla 10, tipo `00`) y nunca a `cbc:ID`. El campo `serie_ubl_sugerida` se eliminó. | `TestMigracion::test_salida_por_venta_queda_pendiente_de_facturar_sin_numero_sunat` |
| 9c | El vale iba en `DespatchDocumentReference` con tipo 09 (guía de remisión). | Va en `cac:AdditionalDocumentReference` con Catálogo 12, tipo `99` (otros). Un vale no se factura dos veces. | `test_el_xml_referencia_el_vale_como_documento_relacionado_99`; `test_un_vale_no_se_factura_dos_veces` |
| 10a | No había formato 14.1. | El dominio tiene `FilaRegistroVentas141` (35 campos), con notas de crédito en negativo, conversión por tipo de cambio y comprobante modificado. Endpoint TXT/JSON con el nombre de archivo PLE. | [`src/domain/libros.py`](../src/domain/libros.py); [`specs/ple/formato-14.1.md`](../specs/ple/formato-14.1.md); `TestRegistroVentas141` |
| 10b | No había formato 12.1 (el "Kardex valorizado" es el 13.1). | Inventario permanente **en unidades físicas**: establecimiento, tipo de existencia (tabla 5), tipo de operación (tabla 12), documento de soporte (tabla 10) y saldo final. El ingreso o salida del sistema antiguo es la materia prima. | `Kardex`, `inventario_121`; [`specs/ple/formato-12.1.md`](../specs/ple/formato-12.1.md); `TestInventario121` |
| 10c | El PLE usa la tabla 6, no UNECE; hacía falta una tabla de equivalencias. | `UnidadMedida.unidad_ple`: Catálogo 03 → tabla 6 (KGM→01, NIU→07, BX→12…). Además hay homologación de glosas antiguas con factor de conversión (1 saco = 50 KGM). | `TestEquivalenciaUnidades`; `test_salida_por_venta_queda_pendiente_de_facturar_sin_numero_sunat` (5 sacos → 250 KGM) |

## 5. Orden del repositorio

| Observación | Corrección |
|---|---|
| Dos ADR con número 0001. | ADR 0001 a 0008, uno por decisión, en [`specs/adr/`](../specs/adr). |
| Dos especificaciones 001 con la matriz duplicada. | Una sola especificación BDD ([`specs/features/001-facturacion-e-inventario.md`](../specs/features/001-facturacion-e-inventario.md)) y una sola matriz ([`specs/traceability/matriz-trazabilidad.md`](../specs/traceability/matriz-trazabilidad.md)). |
| Plantilla XML en `specs/templates`. | Eliminada. En su lugar, [`docs/ejemplos/`](ejemplos) contiene **salidas reales** generadas por el sistema (`python scripts/generar_ejemplos.py`). |

## Segunda iteración: completar lo que la revisión no alcanzó a pedir

Después de la corrección se hizo una revisión de cobertura contra el enunciado completo, no solo contra las observaciones. Se agregó:

| Hueco | Qué se hizo | Evidencia |
|---|---|---|
| No había forma de pago (RS 193-2020, obligatoria en facturas) | `FormaPago` con cuotas en el dominio, el XML (`cac:PaymentTerms`) y el 14.1 (campo 5, si vence hasta el mes siguiente) | `TestFormaPago`, `test_forma_de_pago_credito_con_monto_pendiente_y_cuotas` |
| Faltaba la leyenda 1000 (importe en letras) | `importe_en_letras` propio, con apócopes del español | `test_entero_en_letras` |
| La migración trataba todo `nro_documento` como vale | Clasificación según la tabla 10 (factura, boleta, guía, interno) y estado `FACTURADA_EN_SISTEMA_ANTIGUO` | `TestClasificacionDocumentoLegado` |
| La migración no aceptaba datos reales del sistema antiguo | Fechas en 5 formatos y lotes que no se detienen, con fichas OBSERVADAS, DUPLICADAS y conciliación | `TestLoteDeMigracion`; [ADR 0009](../specs/adr/0009-migracion-por-lotes-y-clasificacion-de-documentos.md) |
| La matriz estaba escrita a mano | YAML único → MD + CSV, con cardinalidad **calculada del XSD** y cada XPath **evaluado contra XML generados** | `tests/integration/test_matriz.py` |
| Solo había ejemplos válidos | 16 contraejemplos con su HTTP y su código esperados | `test_cada_contraejemplo_se_rechaza_como_se_espera` |
| Faltaban los puntos 1 a 3 del enunciado | Análisis del caso, marco normativo, casos de uso y atributos de calidad | [`docs/analisis/`](analisis) |
| Taller 2 | Suite de generación del XML, regresión byte a byte y CLI | [`docs/TALLER-2-generacion-xml.md`](TALLER-2-generacion-xml.md) |
| Los TXT del PLE no se habían contrastado con la fuente oficial | Estructura del Anexo 2 como dato del dominio, verificada contra el Excel oficial de SUNAT; validación de cada campo antes de entregar el TXT | `tests/unit/ple/`, `test_ple_extremo_a_extremo.py`; [ADR 0010](../specs/adr/0010-estructura-ple-en-el-dominio-validada-contra-el-anexo-2.md) |

Las pruebas de generación encontraron además un defecto real: los importes en cero salían como `0` en lugar de `0.00`. Ya está corregido y verificado.

El contraste con el Excel oficial del PLE encontró seis defectos más, todos corregidos y con su prueba:

- al 12.1 le faltaban los campos 8 y 9 (UNSPSC/GTIN), así que tenía 17 campos en lugar de 19;
- las salidas del 12.1 iban en positivo;
- el nombre del archivo de un libro vacío indicaba "baja del RUC";
- el campo 5 del 14.1 no respetaba el límite del mes siguiente;
- la boleta a cliente no identificado llevaba tipo de documento `0`;
- había caracteres no permitidos en los campos de texto y alfanuméricos.

El detalle está en el [ADR 0010](../specs/adr/0010-estructura-ple-en-el-dominio-validada-contra-el-anexo-2.md).

## Aciertos que se conservaron

- **Catálogo 08** con `cbc:TierRange`. Ahora además se **calcula** el ISC de los tres sistemas.
- **TaxScheme** 1000/IGV/VAT, 2000/ISC/EXC y 7152/ICBPER/OTH, `CustomizationID` 2.0 y `TaxExemptionReasonCode`.
- **Ciclo rojo → verde**: se pasó de 20 a 484 pruebas, incluidas pruebas de arquitectura, de contrato y de la matriz.
- **Los puertos del diagrama hexagonal**, que ahora existen en el código.
- **Diagnóstico RS 234-2006 y distribución MSI/APK**, conservados en el ADR 0008.

## Límites declarados

- **OSE.** La OSE es un adaptador **simulado**: verifica la firma y el XSD, pero no aplica las más de 1 500 reglas de validación de SUNAT. El adaptador real (SOAP `sendBill` o REST de una OSE) implementa el mismo puerto `ClienteOSE`.
- **Firma.** En desarrollo se usa un certificado autofirmado generado en memoria. En producción se carga el `.pfx` del emisor (`ABC_CERTIFICADO_PFX`).
- **Persistencia.** La persistencia es en memoria. El ADR 0004 describe el adaptador SQL: secuencia con `UPDATE … RETURNING` y restricción `UNIQUE`.
- **Fuera de alcance.** No se soportan las operaciones gratuitas (afectaciones 11-17, 21, 31-37), los anticipos, las detracciones, el resumen diario de boletas ni la comunicación de baja.
- **PLE.** La estructura de los TXT 14.1 y 12.1 se verifica automáticamente contra el Excel oficial del Anexo 2 de la RS 286-2009/SUNAT (PLE 5.0). Falta cargarlos en el programa PLE de escritorio, que aplica además validaciones contra el padrón RUC; la estructura está aislada en `ple_estructura.py`, así que una nueva versión del Anexo 2 se actualiza en un solo lugar.
