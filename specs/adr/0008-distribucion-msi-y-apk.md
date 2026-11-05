# ADR 0008: Distribución multiplataforma (Windows MSI y Android APK)

- **Estado:** aceptado. La estrategia viene de la versión anterior, que la revisión reconoció como acierto. **Revisado el 2026-11-05:** la versión anterior decía "Flutter **o** Kotlin" y no decidía. Ahora se elige una tecnología por plataforma, con las alternativas evaluadas.
- **Depende de:** ADR 0001 (hexagonal), ADR 0011 (SQLite) y ADR 0013 (contrato en JSON Schema).

## Contexto

ABC Software Corp necesita dos clientes:

- **Cajas Windows (POS)** en las sucursales. Deben seguir vendiendo si se cae internet.
- **Terminales Android** para los almaceneros, que registran ingresos y salidas en zonas del almacén sin cobertura.

Restricciones del caso:

- el núcleo de negocio (cálculo tributario, reglas SUNAT, Kardex) ya existe en Python y está probado;
- el equipo es pequeño y no puede mantener dos implementaciones de las reglas tributarias;
- los instaladores deben poder firmarse (Authenticode en Windows, firma de APK/AAB en Android).

## Alternativas evaluadas

Escala: ●●● bueno · ●● aceptable · ● débil.

### Escritorio Windows (MSI)

| Criterio | **PyInstaller + WiX** | Briefcase (BeeWare) | Nuitka + WiX |
|---|:-:|:-:|:-:|
| Reutiliza el núcleo Python sin cambios | ●●● mismo código, mismo `bootstrap.py` | ●●● | ●●● |
| Funciona sin conexión (API local + SQLite + cola) | ●●● | ●●● | ●●● |
| MSI nativo, actualizable con `MajorUpgrade` y desplegable por GPO | ●●● WiX genera el MSI directamente | ●● genera MSI con su propia plantilla WiX, menos control | ●●● |
| Firma Authenticode del instalador y del .exe | ●●● `signtool` sobre ambos | ●● | ●●● |
| Madurez con FastAPI, lxml, signxml y cryptography | ●●● hooks oficiales | ● orientado a apps con UI Toga | ●● compila a C; extensiones nativas requieren ajustes |
| Tiempo de compilación en CI | ●●● ~1 min | ●● | ● muy lento (compila C) |
| Costo para el equipo | ●●● una herramienta Python y un XML | ●● | ●● |

**Decisión: PyInstaller (modo carpeta) + WiX Toolset 5.**

- Briefcase está pensado para aplicaciones con interfaz Toga; aquí el entregable es una API local.
- Nuitka ofrece algo de rendimiento y ofuscación que el caso no necesita, a cambio de compilaciones mucho más lentas y ajustes con las extensiones nativas.

### Android (APK/AAB)

| Criterio | **Kotlin nativo** | Flutter | Kivy / Buildozer | Briefcase |
|---|:-:|:-:|:-:|:-:|
| Experiencia nativa: cámara y escáner, tareas en segundo plano | ●●● CameraX + ML Kit, WorkManager | ●● plugins de terceros | ● | ● |
| Operación sin conexión fiable (base local + reintentos) | ●●● Room/SQLite + WorkManager | ●● sqflite + tareas propias | ●● | ●● |
| Reutiliza el núcleo Python | ● no, ver nota | ● no | ●●● | ●●● |
| Reutiliza el **contrato** (JSON Schemas del ADR 0013) | ●●● genera los modelos o valida con los schemas | ●●● | ●● | ●● |
| Tamaño del APK y arranque | ●●● | ●● | ● incluye el intérprete | ● incluye el intérprete |
| Soporte y mantenimiento a largo plazo | ●●● plataforma oficial | ●●● | ● comunidad pequeña | ● experimental en Android |
| Costo para el equipo | ●● un lenguaje nuevo, pero el estándar de Android | ●● Dart | ●● | ●● |

**Decisión: Kotlin nativo.**

**Nota sobre reutilizar el núcleo Python.** La app del almacén **no necesita** el núcleo. No calcula impuestos ni emite comprobantes: captura movimientos y los sincroniza.

- Las reglas del Kardex (saldo, orden cronológico) se validan **en el servidor** al sincronizar.
- La app valida el **formato** localmente con los mismos JSON Schemas del contrato (`ficha-legado.schema.json`, `lote-fichas.schema.json`). Así, la única fuente de verdad compartida es el contrato, no el código.

Por eso pesa más la experiencia nativa (escáner, segundo plano, poco consumo de batería) que reutilizar el núcleo Python, que es el único criterio donde gana Kivy o Briefcase.

## Decisión

**Windows (MSI) con PyInstaller + WiX 5.**
- El mismo `domain` + `application` + adaptador HTTP, empaquetados con Python embebido. Arranca en `127.0.0.1` ([`packaging/windows/abc_local.py`](../../packaging/windows/abc_local.py)), así que no se expone a la red de la sucursal.
- Persistencia SQLite en `%LOCALAPPDATA%\ABC Facturacion\abc.db` (ADR 0011). La cola de envío a la OSE es el estado `PENDIENTE_ENVIO` que ya existe: se reenvía con `POST …/envios` cuando vuelve internet (ADR 0012).
- MSI con `MajorUpgrade` y `UpgradeCode` fijo ([`abc-facturacion.wxs`](../../packaging/windows/abc-facturacion.wxs)). Se distribuye por GPO de Active Directory.
- Firma Authenticode del `.exe` y del `.msi` con `signtool`, con el certificado de código de la empresa (no se versiona).
- **Prototipo funcionando:** el workflow [`instalador-msi.yml`](../../.github/workflows/instalador-msi.yml) corre en `windows-latest`. Empaqueta, prueba el ejecutable (`--salud`), construye el MSI, lo instala en silencio, vuelve a probar `/salud` desde `Program Files` y publica el MSI como artefacto. El ejecutable de PyInstaller se probó además en local: levanta la API y emite la factura de ejemplo (201).

**Android (APK/AAB) con Kotlin nativo.**
- Room (SQLite) para operar sin conexión.
- Escaneo de códigos de barras con CameraX + ML Kit.
- Sincronización con WorkManager al recuperar señal, contra `POST /api/v1/inventario/migraciones/lotes`. Ese endpoint ya está diseñado para lotes que no se detienen ante una ficha observada y devuelve la conciliación.
- Validación local de formato con los JSON Schemas del contrato.
- Firma del AAB con la clave de subida de Google Play o distribución privada por MDM.
- Queda **fuera de este repositorio**: es otro cliente del mismo contrato.

## Por qué depende del ADR 0001

Sin la separación hexagonal no se podría reutilizar el núcleo en el MSI: con el MVC anterior, las reglas estaban atadas a FastAPI y al repositorio en memoria. Hoy, el MSI es el mismo código con otra configuración (`config.py`) y otro empaquetado.

## Consecuencias

- Hay un pipeline de empaquetado por plataforma, pero las reglas de negocio viven en un solo lugar (el servidor y el MSI comparten el núcleo; la app Android comparte el contrato).
- Agregar un canal es agregar un adaptador o un cliente del contrato, no reescribir reglas.
- El MSI no incluye todavía servicio de Windows ni acceso directo en el menú Inicio: es un prototipo que demuestra que el empaquetado y la instalación funcionan.
