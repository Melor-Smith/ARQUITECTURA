# Arquitectura: de MVC a Hexagonal (Puertos y Adaptadores)

Este documento describe **lo que está implementado**. Cada caja de los diagramas es un módulo que existe en `src/`, y las reglas de dependencia se verifican con pruebas automáticas (`tests/integration/test_arquitectura.py`).

## Diagramas renderizados

Las fuentes Mermaid están en [`docs/diagramas/`](../../docs/diagramas) y se renderizan con `scripts/renderizar_diagramas.ps1`. `tests/integration/test_diagramas.py` falla si a un `.mmd` le falta su `.svg` o su `.png`.

| # | Diagrama | Qué muestra | Archivos |
|:-:|---|---|---|
| 01 | **Contexto C4 (nivel 1)** | ABC, cajeros, almaceneros, contador, SUNAT/OSE, sistema antiguo y programa PLE | [SVG](../../docs/diagramas/01-contexto-c4.svg) · [PNG](../../docs/diagramas/01-contexto-c4.png) · [fuente](../../docs/diagramas/01-contexto-c4.mmd) |
| 02 | **Contenedores C4 (nivel 2)** | API FastAPI, CLI, núcleo, SQLite, generador UBL, firma y cliente SOAP de SUNAT | [SVG](../../docs/diagramas/02-contenedores-c4.svg) · [PNG](../../docs/diagramas/02-contenedores-c4.png) · [fuente](../../docs/diagramas/02-contenedores-c4.mmd) |
| 03 | **MVC dentro del adaptador HTTP** | Controladores, vistas JSON/XML/TXT y el núcleo como Modelo (§2) | [SVG](../../docs/diagramas/03-mvc-actual.svg) · [PNG](../../docs/diagramas/03-mvc-actual.png) · [fuente](../../docs/diagramas/03-mvc-actual.mmd) |
| 04 | **Hexagonal** | Puertos `Protocol` y sus adaptadores: memoria/SQLite, xsdata, signxml, SOAP/simulada (§3) | [SVG](../../docs/diagramas/04-hexagonal.svg) · [PNG](../../docs/diagramas/04-hexagonal.png) · [fuente](../../docs/diagramas/04-hexagonal.mmd) |
| 05 | **Evolución** | MVC del primer entregable → hexagonal actual → microservicios (facturación, inventario, libros) | [SVG](../../docs/diagramas/05-evolucion.svg) · [PNG](../../docs/diagramas/05-evolucion.png) · [fuente](../../docs/diagramas/05-evolucion.mmd) |
| 06 | **Clases del dominio** | `Comprobante`, `Linea`, `Totales`, `FormaPago`, `Cuota`, `Kardex`, `MigracionLegado` y objetos de valor (§6) | [SVG](../../docs/diagramas/06-clases-dominio.svg) · [PNG](../../docs/diagramas/06-clases-dominio.png) · [fuente](../../docs/diagramas/06-clases-dominio.mmd) |
| 07 | **Secuencia de emisión** | POST → validar → calcular → XML → XSD → firmar → `sendBill` → CDR → estado (§4) | [SVG](../../docs/diagramas/07-secuencia-emision.svg) · [PNG](../../docs/diagramas/07-secuencia-emision.png) · [fuente](../../docs/diagramas/07-secuencia-emision.mmd) |
| 08 | **Estados del comprobante** | Máquina de estados según el CDR (§5) | [SVG](../../docs/diagramas/08-estados-comprobante.svg) · [PNG](../../docs/diagramas/08-estados-comprobante.png) · [fuente](../../docs/diagramas/08-estados-comprobante.mmd) |
| 09 | **Despliegue** | Docker y volumen `/datos`, SUNAT beta/producción, MSI y APK (§8) | [SVG](../../docs/diagramas/09-despliegue.svg) · [PNG](../../docs/diagramas/09-despliegue.png) · [fuente](../../docs/diagramas/09-despliegue.mmd) |

![Arquitectura hexagonal](../../docs/diagramas/04-hexagonal.svg)

## 1. Por qué la versión anterior no era migrable

| Síntoma | Consecuencia |
|---|---|
| `src/services` importaba de `tests/mocks` | Producción dependía de los datos de prueba |
| Servicios con `@classmethod` que llamaban al repositorio concreto | Sin puntos de inyección: imposible cambiar la memoria por una base de datos o la OSE simulada por la real |
| El "Modelo" eran DTOs de Pydantic | La regla de negocio quedaba atada al framework web y no había entidades con comportamiento |
| La "Vista" era el YAML de OpenAPI | Se confundía el **contrato** con la **representación** |
| Los puertos solo existían en el diagrama | El diagrama hexagonal no tenía correlato en el código |

## 2. Dónde vive MVC ahora

MVC es un patrón de **presentación**. En una arquitectura hexagonal no desaparece: queda **dentro del adaptador de entrada HTTP**, y el "Modelo" que consume es el núcleo de la aplicación.

| MVC | Implementación | Responsabilidad |
|---|---|---|
| **Controlador** | [`adapters/inbound/http/controladores/`](../../src/adapters/inbound/http/controladores) | Traduce HTTP ↔ comando, invoca el caso de uso y elige la vista. Sin reglas de negocio |
| **Modelo** | [`application/`](../../src/application) (casos de uso) y [`domain/`](../../src/domain) (entidades y reglas) | Toda la lógica: cálculo tributario, reglas SUNAT, Kardex, máquina de estados |
| **Vista** | [`adapters/inbound/http/vistas/`](../../src/adapters/inbound/http/vistas) | Representaciones del modelo: **JSON**, **XML UBL firmado** y **TXT del PLE** |
| *(contrato, no vista)* | [`specs/contracts/openapi.yaml`](../contracts/openapi.yaml) | Describe las vistas y las entradas. Se escribe **primero, a mano**, y los DTO lo implementan ([ADR 0013](../adr/0013-contrato-escrito-primero-y-verificado-contra-el-codigo.md)) |

## 3. Hexágono implementado

```mermaid
flowchart LR
    subgraph IN["Adaptadores de entrada"]
        HTTP["HTTP FastAPI<br/>controladores + vistas + DTO Pydantic<br/>problem+json, Bearer"]
        CLI["CLI generar-xml<br/>src/adapters/inbound/cli.py"]
        TR["traduccion.py<br/>DTO → comando (compartido)"]
    end

    subgraph APP["Aplicación: src/application"]
        UC1["EmitirComprobante"]
        UC2["ConsultarComprobante<br/>ReenviarComprobante"]
        UC3["MigrarFichaLegado · MigrarLoteLegado<br/>ConsultarKardex / Migracion / Lote"]
        UC4["GenerarRegistroVentas141<br/>GenerarInventario121"]
        P["puertos.py (Protocol)"]
    end

    subgraph DOM["Dominio: src/domain (solo stdlib)"]
        D1["Comprobante, BorradorComprobante<br/>Linea, Totales, Cdr, FormaPago"]
        D2["Ruc, Serie, Correlativo<br/>NumeroComprobante"]
        D3["tributos: IGV, ISC Cat. 08, ICBPER"]
        D4["Kardex, FichaLegado, MigracionLegado<br/>clasificar_documento_legado"]
        D5["libros: filas 14.1 y 12.1"]
    end

    subgraph OUT["Adaptadores de salida"]
        A1["persistencia: memoria.py y sqlite.py<br/>mismos puertos; transacciones, secuencia atómica"]
        A2["ubl/generador.py (xsdata)<br/>ubl/validador.py (lxml + XSD)"]
        A3["firma/xmldsig.py (signxml)"]
        A4["ose/simulada.py y ose/sunat_soap.py<br/>(SOAP sendBill de SUNAT)"]
        A5["reloj.py (UTC-5)"]
    end

    HTTP --> TR
    CLI --> TR
    TR --> UC1 & UC2
    HTTP --> UC3 & UC4
    UC1 & UC2 & UC3 & UC4 --> DOM
    UC1 & UC2 & UC3 & UC4 --> P
    A1 & A2 & A3 & A4 & A5 -. implementan .-> P
```

**Regla de dependencias** (las flechas apuntan hacia adentro):

- `domain` solo importa la biblioteca estándar y `src.domain`.
- `application` importa `domain` y sus propios módulos.
- Los adaptadores importan `application` y `domain`.
- **Ningún** módulo de `src/` importa de `tests/`.

La raíz de composición [`src/bootstrap.py`](../../src/bootstrap.py) es el único lugar que conoce las clases concretas.

**Dos adaptadores de entrada, un solo núcleo.** La API HTTP y la línea de comandos (`python -m src.adapters.inbound.cli generar-xml …`, del Taller 2) traducen el mismo contrato con [`traduccion.py`](../../src/adapters/inbound/traduccion.py) y ejecutan el **mismo** caso de uso `EmitirComprobante`. Agregar un canal (escritorio MSI, app APK) es agregar un adaptador, no tocar las reglas.

### Puertos de salida

| Puerto (`application/puertos.py`) | Adaptador actual | Adaptador de producción (mismo puerto) |
|---|---|---|
| `RepositorioComprobantes`, `RepositorioKardex`, `RepositorioMigraciones`, `RepositorioProductos`, `RepositorioIdempotencia`, `RepositorioLotes` | `persistencia/memoria.py` **y** `persistencia/sqlite.py` (se elige con `ABC_BASE_DATOS`; [ADR 0011](../adr/0011-persistencia-sqlite-como-segundo-adaptador.md)) | PostgreSQL con los mismos puertos y el mismo SQL |
| `SecuenciaCorrelativos` | En memoria con bloqueo **y** SQLite: `INSERT … ON CONFLICT DO UPDATE … RETURNING` | Igual en PostgreSQL |
| `UnidadDeTrabajo` | `RLock` en memoria **y** transacción SQLite con `SAVEPOINT` anidados | Transacción SQL |
| `GeneradorUBL` | `GeneradorUblXsdata` | — (es definitivo) |
| `ValidadorEsquemaUBL` | `ValidadorXsdLxml` | — |
| `FirmaDigital` | `FirmaXmlDsig` con certificado autofirmado | `FirmaXmlDsig` con el `.pfx` del emisor |
| `ClienteOSE` | `OseSimulada` **y** `ClienteSunatSoap` (SOAP `sendBill`, probado contra el servicio beta de SUNAT; se elige con `ABC_SUNAT_ENDPOINT`; [ADR 0012](../adr/0012-envio-real-a-sunat-y-validacion-contra-el-servicio-beta.md)) | `ClienteSunatSoap` con certificado y usuario SOL reales |
| `Reloj` | `RelojSistema` / `RelojFijo` | — |

## 4. Flujo de emisión

```mermaid
sequenceDiagram
    autonumber
    participant C as Cliente HTTP
    participant Ctl as Controlador
    participant UC as EmitirComprobante
    participant Dom as Dominio
    participant Seq as SecuenciaCorrelativos
    participant UBL as GeneradorUBL + Validador
    participant F as FirmaDigital
    participant O as ClienteOSE

    C->>Ctl: POST /api/v1/comprobantes (sin impuestos, totales ni correlativo)
    Ctl->>Ctl: DTO Pydantic (formato) → 400 si falla
    Ctl->>UC: EmitirComprobanteCmd
    rect rgb(240,240,240)
    note over UC,F: Transacción (UnidadDeTrabajo)
    UC->>UC: ¿Idempotency-Key repetida? → 200 / 409
    UC->>Dom: Linea.calcular (IGV, ISC, ICBPER con Decimal)
    UC->>Dom: BorradorComprobante.preparar (reglas cruzadas) → 422
    UC->>Dom: Kardex.verificar (saldo) → 422
    UC->>Seq: siguiente(ruc, tipo, serie): reserva atómica
    UC->>UBL: generar → validar XSD (antes de firmar)
    UC->>F: firmar (XMLDSig en ext:UBLExtensions)
    UC->>UBL: validar XSD (después de firmar)
    UC->>Dom: registrar_firma, Kardex.registrar, vale legado → FACTURADA
    end
    UC->>O: enviar (fuera de la transacción)
    alt OSE responde CDR
        O-->>UC: Cdr(0 / 2xxx / 4xxx)
        UC->>Dom: registrar_cdr → ACEPTADO / RECHAZADO (revierte el Kardex)
        Ctl-->>C: 201 + Location (estado tomado del CDR)
    else OSE caída o respuesta inválida
        UC->>Dom: registrar_envio_fallido → PENDIENTE_ENVIO
        Ctl-->>C: 202 + Location (reintento: POST …/envios → 200 / 409 / 502 / 503)
    end
```

Decisiones clave del flujo:

- **Todas las reglas se validan antes de reservar el correlativo.** Un 422 no deja huecos en la numeración.
- **El envío a la OSE va fuera de la transacción.** Es E/S remota, puede tardar, y no debe bloquear otras emisiones.

## 5. Máquina de estados del comprobante

```mermaid
stateDiagram-v2
    [*] --> REGISTRADO: numerado, validado y firmado
    REGISTRADO --> ACEPTADO: CDR 0
    REGISTRADO --> ACEPTADO_CON_OBSERVACIONES: CDR 0 con observaciones o ≥ 4000
    REGISTRADO --> RECHAZADO: CDR 2000-3999
    REGISTRADO --> PENDIENTE_ENVIO: OSE caída o respuesta inválida
    PENDIENTE_ENVIO --> PENDIENTE_ENVIO: reintento fallido (503 / 502)
    PENDIENTE_ENVIO --> ACEPTADO
    PENDIENTE_ENVIO --> ACEPTADO_CON_OBSERVACIONES
    PENDIENTE_ENVIO --> RECHAZADO
    ACEPTADO --> [*]
    ACEPTADO_CON_OBSERVACIONES --> [*]
    RECHAZADO --> [*]
```

Cualquier intento de reenviar un comprobante que ya tiene CDR responde 409 (`ERR-COMPROBANTE-YA-PROCESADO`).

## 6. Modelo de dominio

```mermaid
classDiagram
    class Comprobante {
        +TipoComprobante tipo
        +NumeroComprobante numero
        +EstadoComprobante estado
        +str hash_cpe
        +registrar_firma()
        +registrar_cdr(cdr)
        +registrar_envio_fallido()
    }
    class BorradorComprobante {
        +preparar()
        +numerar(correlativo)
    }
    class NumeroComprobante {
        +Serie serie
        +Correlativo correlativo
    }
    class Linea {
        +UnidadMedida unidad
        +AfectacionIGV afectacion
        +ConfiguracionISC isc
        +calcular()
    }
    class Totales {
        +de_lineas()
    }
    class Cliente {
        +DocumentoIdentidad documento
    }
    class Emisor {
        +Ruc ruc
    }
    class Kardex {
        +Decimal saldo
        +verificar()
        +registrar()
    }
    class MovimientoInventario {
        +TipoOperacionInventario tipo_operacion
        +DocumentoSoporte documento
    }
    class MigracionLegado {
        +EstadoMigracion estado
        +marcar_facturada()
    }
    class FichaLegado {
        +date fecha
        +Decimal ingreso
        +Decimal salida
        +str producto
        +str nro_documento
    }

    BorradorComprobante ..> Comprobante : numerar
    Comprobante *-- NumeroComprobante
    Comprobante *-- "1..*" Linea
    Comprobante *-- Totales
    Comprobante --> Cliente
    Comprobante --> Emisor
    Comprobante --> "0..1" Comprobante : referencia (notas)
    Kardex *-- "*" MovimientoInventario
    MigracionLegado --> FichaLegado
    MigracionLegado --> MovimientoInventario
```

## 7. Correspondencia con la versión anterior

| Antes | Ahora |
|---|---|
| `src/models/schemas.py` (DTO usado como modelo) | Dominio en `src/domain/*`; DTO en `adapters/inbound/http/esquemas.py` |
| `src/services/sunat_ubl_service.py` (estático, f-strings) | Casos de uso en `application/casos_uso/*`; XML en `adapters/outbound/ubl/*`; firma en `adapters/outbound/firma` |
| `src/repositories/memory_repo.py` → `tests/mocks` | `adapters/outbound/persistencia/memoria.py` + `semillas.py`, inyectados |
| `src/controllers/factura_controller.py` | `adapters/inbound/http/controladores/*` |
| `src/views/presenters.py` | `adapters/inbound/http/vistas/*` (JSON, XML, TXT) |
| `specs/contracts/ubl-invoice-api.yaml` (a mano, divergente) | `specs/contracts/openapi.yaml` + `schemas/*.schema.json` (escritos primero; el código se verifica contra ellos) |

## 8. Distribución

La estrategia MSI (Windows, puntos de venta) y APK (Android, almacén sin conexión) se mantiene en el [ADR 0008](../adr/0008-distribucion-msi-y-apk.md). La arquitectura hexagonal es lo que la hace viable: el mismo `domain` + `application` se empaqueta con otros adaptadores de entrada (UI de escritorio, app móvil) y de salida (SQLite local, cola de sincronización), sin tocar las reglas.
