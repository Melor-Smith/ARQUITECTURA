"""Raíz de composición: el ÚNICO lugar que conoce las implementaciones concretas.

Aquí se eligen los adaptadores y se inyectan en los casos de uso. Cambiar la memoria por
PostgreSQL, o la OSE simulada por la real, se hace solo en este archivo.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.adapters.outbound.firma.xmldsig import CertificadoDigital, FirmaXmlDsig
from src.adapters.outbound.ose.simulada import OseSimulada
from src.adapters.outbound.persistencia import semillas
from src.adapters.outbound.persistencia.memoria import (
    GeneradorIdentificadoresEnMemoria,
    RepositorioComprobantesEnMemoria,
    RepositorioIdempotenciaEnMemoria,
    RepositorioKardexEnMemoria,
    RepositorioLotesEnMemoria,
    RepositorioMigracionesEnMemoria,
    RepositorioProductosEnMemoria,
    SecuenciaCorrelativosEnMemoria,
    UnidadDeTrabajoEnMemoria,
)
from src.adapters.outbound.reloj import RelojSistema
from src.adapters.outbound.ubl.generador import GeneradorUblXsdata
from src.adapters.outbound.ubl.validador import ValidadorXsdLxml
from src.application.casos_uso.comprobantes import ConsultarComprobante, EmitirComprobante, ReenviarComprobante
from src.application.casos_uso.inventario import (
    ConsultarKardex,
    ConsultarLote,
    ConsultarMigracion,
    MigrarFichaLegado,
    MigrarLoteLegado,
)
from src.application.casos_uso.libros import GenerarInventario121, GenerarRegistroVentas141
from src.application.puertos import ClienteOSE, Reloj
from src.config import Configuracion
from src.domain.comprobante import Emisor


@dataclass
class Contenedor:
    configuracion: Configuracion
    emisor: Emisor
    ose: ClienteOSE
    emitir_comprobante: EmitirComprobante
    consultar_comprobante: ConsultarComprobante
    reenviar_comprobante: ReenviarComprobante
    migrar_ficha_legado: MigrarFichaLegado
    migrar_lote_legado: MigrarLoteLegado
    consultar_lote: ConsultarLote
    consultar_migracion: ConsultarMigracion
    consultar_kardex: ConsultarKardex
    registro_ventas_141: GenerarRegistroVentas141
    inventario_121: GenerarInventario121


_VALIDADOR = ValidadorXsdLxml()  # los XSD se compilan una vez y se reutilizan


def construir_contenedor(
    configuracion: Configuracion | None = None,
    *,
    reloj: Reloj | None = None,
    ose: ClienteOSE | None = None,
    emisor: Emisor = semillas.EMISOR_ABC,
    cargar_semillas: bool = True,
    ultimos_correlativos: dict[tuple[str, str], int] | None = None,
) -> Contenedor:
    """``ultimos_correlativos``: {(tipo, serie): último número ya emitido} para continuar series existentes."""
    configuracion = configuracion or Configuracion.desde_entorno()
    reloj = reloj or RelojSistema()
    establecimiento = emisor.codigo_establecimiento

    uow = UnidadDeTrabajoEnMemoria()
    ids = GeneradorIdentificadoresEnMemoria()
    comprobantes = RepositorioComprobantesEnMemoria()
    productos = RepositorioProductosEnMemoria(semillas.PRODUCTOS, semillas.HOMOLOGACIONES)
    kardex = RepositorioKardexEnMemoria()
    migraciones = RepositorioMigracionesEnMemoria()
    if cargar_semillas:
        semillas.cargar_saldos_iniciales(kardex, ids, establecimiento)

    if configuracion.certificado_pfx:
        certificado = CertificadoDigital.desde_pfx(configuracion.certificado_pfx,
                                                   configuracion.contrasena_certificado)
    else:
        certificado = CertificadoDigital.autofirmado_para_desarrollo(str(emisor.ruc), emisor.razon_social)

    ose = ose or OseSimulada(validador=_VALIDADOR, reloj=reloj, modo=configuracion.modo_ose)
    emitir = EmitirComprobante(
        emisor=emisor,
        plazo_envio_dias=configuracion.plazo_envio_dias,
        reloj=reloj,
        uow=uow,
        secuencia=SecuenciaCorrelativosEnMemoria(
            {(str(emisor.ruc), tipo, serie): ultimo for (tipo, serie), ultimo in (ultimos_correlativos or {}).items()}
        ),
        comprobantes=comprobantes,
        idempotencia=RepositorioIdempotenciaEnMemoria(),
        productos=productos,
        kardex=kardex,
        migraciones=migraciones,
        ids=ids,
        generador_ubl=GeneradorUblXsdata(),
        validador_xsd=_VALIDADOR,
        firma=FirmaXmlDsig(certificado),
        ose=ose,
    )
    consultar = ConsultarComprobante(comprobantes=comprobantes)
    lotes = RepositorioLotesEnMemoria()
    migrar = MigrarFichaLegado(uow=uow, productos=productos, kardex=kardex, migraciones=migraciones, ids=ids,
                               establecimiento_por_defecto=establecimiento)
    return Contenedor(
        configuracion=configuracion,
        emisor=emisor,
        ose=ose,
        emitir_comprobante=emitir,
        consultar_comprobante=consultar,
        reenviar_comprobante=ReenviarComprobante(consultar=consultar, envio=emitir.envio),
        migrar_ficha_legado=migrar,
        migrar_lote_legado=MigrarLoteLegado(uow=uow, migrar=migrar, kardex=kardex, lotes=lotes, ids=ids, reloj=reloj),
        consultar_lote=ConsultarLote(lotes=lotes),
        consultar_migracion=ConsultarMigracion(migraciones=migraciones),
        consultar_kardex=ConsultarKardex(productos=productos, kardex=kardex,
                                         establecimiento_por_defecto=establecimiento),
        registro_ventas_141=GenerarRegistroVentas141(ruc=emisor.ruc, comprobantes=comprobantes),
        inventario_121=GenerarInventario121(ruc=emisor.ruc, kardex=kardex),
    )
