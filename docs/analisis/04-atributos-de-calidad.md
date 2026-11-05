# 4. Atributos de calidad (requisitos no funcionales)

Cada atributo tiene una meta verificable y la evidencia que hoy la respalda. Si la evidencia es "pendiente", así se indica.

| ID | Atributo | Meta | Evidencia actual |
|---|---|---|---|
| AC-01 | **Exactitud tributaria** | 0 diferencias entre los totales calculados y el XML; importes siempre con 2 decimales | `tests/unit/test_tributos.py`; `test_tax_total_de_cada_linea_suma_sus_subtotales`; auditoría de decimales en los XML de referencia |
| AC-02 | **Rendimiento** | p95 de la emisión completa (cálculo, XML, validación XSD ×2, firma y OSE simulada) < 500 ms en el proceso | `tests/integration/test_rendimiento.py`: **mediana 8,8 ms, p95 10,2 ms** en el equipo de desarrollo, sin red. La latencia de la OSE real se suma aparte |
| AC-03 | **Integridad** | XML firmado; cualquier alteración posterior se detecta | `test_la_ose_simulada_acepta_y_detecta_un_xml_alterado_despues_de_firmar`; SUNAT real también lo rechaza con 2335 (respuesta grabada de beta en `test_firma_alterada_es_rechazo_2335`) |
| AC-04 | **Consistencia de la numeración** | Correlativo único y sin huecos por rechazos de negocio, aun con concurrencia | `test_concurrencia.py` (200 reservas concurrentes); `test_rechazo_de_negocio_no_consume_correlativo` |
| AC-05 | **Disponibilidad de la venta** | La venta no se bloquea si la OSE cae | `TestOse`: 202 + reenvío; 503 con `Retry-After` |
| AC-06 | **Conformidad del contrato** | El contrato publicado y el código no divergen | `test_el_openapi_versionado_coincide_con_el_generado_por_el_codigo`; 16 contraejemplos |
| AC-07 | **Mantenibilidad / evolución** | El dominio no depende de frameworks; los adaptadores son sustituibles | `test_arquitectura.py`; dos adaptadores de entrada (HTTP y CLI) sobre los mismos casos de uso |
| AC-08 | **Seguridad** | Autenticación y autorización por alcance; sin XXE; secretos fuera del repositorio | `TestSeguridad`; `test_el_parser_no_resuelve_entidades_externas_xxe`; `.gitignore` de `*.pfx` y `*.pem` |
| AC-09 | **Trazabilidad** | Cada dato normativo tiene su XPath, campo de contrato, libro PLE y prueba | `tests/integration/test_matriz.py` (64 XPath evaluados contra XML reales) |
| AC-10 | **Recuperabilidad de la migración** | Reprocesar un lote no duplica movimientos; cada lote se concilia | `test_reprocesar_el_mismo_lote_es_seguro`; conciliación por producto |
| AC-11 | **Portabilidad** | Windows (MSI) y Android (APK) | Diseño en el [ADR 0008](../../specs/adr/0008-distribucion-msi-y-apk.md); **pendiente de implementar** |
| AC-12 | **Conservación** | XML y CDR disponibles durante el plazo legal | **Cumplido con SQLite** (`ABC_BASE_DATOS`; volumen `/datos` en Docker): el XML firmado y el CDR sobreviven a reinicios (`test_los_datos_sobreviven_a_un_reinicio_y_el_correlativo_continua`). Para el plazo legal completo hace falta además una política de respaldo |
