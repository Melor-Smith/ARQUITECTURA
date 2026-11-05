# ADR 0008: Distribución multiplataforma (Windows MSI y Android APK)

- **Estado:** aceptado. Se conserva de la versión anterior, donde la revisión lo reconoció como acierto.

## Contexto

ABC Software Corp necesita estaciones de caja Windows (POS) en las sucursales y terminales Android para los almaceneros, que registran ingresos y salidas en zonas del almacén sin cobertura.

## Decisión

**Windows (MSI).**
- Binario autocontenido con PyInstaller, empaquetado con WiX Toolset v4.
- Firma Authenticode y despliegue por GPO de Active Directory.
- Se ejecuta como servicio local para las sincronizaciones nocturnas.
- Reutiliza `domain` + `application` con un adaptador de entrada de escritorio. En sucursales sin conexión estable, usa además un adaptador de salida SQLite con cola de envío a la OSE.

**Android (APK/AAB).**
- Aplicación Flutter o Kotlin con almacenamiento SQLite cifrado (SQLCipher) para operar sin conexión.
- Escaneo de códigos de barras y sincronización con la API central al recuperar la conexión.
- La captura de movimientos de almacén usa el mismo contrato que `POST /api/v1/inventario/migraciones`, y las reglas del Kardex (saldo, orden cronológico) se validan en el servidor al sincronizar.

## Por qué depende del ADR 0001

Sin la separación hexagonal no se podría reutilizar el núcleo: con el MVC anterior, las reglas estaban atadas a FastAPI y al repositorio en memoria.

## Consecuencias

Hay que mantener un pipeline de empaquetado por plataforma, pero el núcleo de negocio es uno solo.
