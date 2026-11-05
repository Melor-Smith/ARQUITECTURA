"""Controlador (la C de MVC) de comprobantes. Sin reglas de negocio: traduce HTTP <-> comando."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Header, Path, Request, Response

from src.adapters.inbound.http.esquemas import (
    PATRON_SERIE_NUMERO,
    BoletaEntrada,
    ComprobanteSalida,
    FacturaEntrada,
    NotaCreditoEntrada,
    NotaDebitoEntrada,
)
from src.adapters.inbound.http.openapi import ejemplos_openapi, respuestas
from src.adapters.inbound.http.seguridad import requiere
from src.adapters.inbound.http.vistas.comprobante import comprobante_json, comprobante_xml, ruta
from src.adapters.inbound.traduccion import comando_emision
from src.bootstrap import Contenedor
from src.domain.catalogos import TipoComprobante
from src.domain.comprobante import EstadoComprobante

router = APIRouter(prefix="/api/v1/comprobantes", tags=["Comprobantes"])

CuerpoComprobante = Annotated[
    FacturaEntrada | BoletaEntrada | NotaCreditoEntrada | NotaDebitoEntrada,
    Body(
        discriminator="tipo_comprobante",
        openapi_examples=ejemplos_openapi(
            factura="factura.json",
            factura_con_isc_e_icbper="factura-isc-icbper.json",
            factura_al_credito="factura-credito.json",
            factura_de_vale_legado="factura-de-vale-legado.json",
            boleta="boleta.json",
            nota_de_credito="nota-credito.json",
            nota_de_debito="nota-debito.json",
        ),
    ),
]
TipoPath = Annotated[TipoComprobante, Path(description="Catálogo 01: 01, 03, 07 u 08.")]
SerieNumeroPath = Annotated[str, Path(pattern=PATRON_SERIE_NUMERO, description="cbc:ID, p. ej. F001-1.",
                                      examples=["F001-1"])]


def _contenedor(request: Request) -> Contenedor:
    return request.app.state.contenedor


@router.post(
    "",
    status_code=201,
    response_model=ComprobanteSalida,
    dependencies=[requiere("comprobantes:emitir")],
    summary="Emite una factura, boleta, nota de crédito o nota de débito",
    description=(
        "Valida las reglas SUNAT, calcula IGV, ISC (Catálogo 08) e ICBPER con Decimal, asigna el correlativo de "
        "forma atómica, genera el XML UBL 2.1 desde clases del XSD, lo valida, lo firma (XMLDSig) y lo envía a la "
        "OSE. El cliente NO envía impuestos, totales ni correlativo.\n\n"
        "* **201**: la OSE devolvió CDR; el estado (`ACEPTADO`, `ACEPTADO_CON_OBSERVACIONES` o `RECHAZADO`) "
        "sale de ese CDR.\n"
        "* **202**: comprobante firmado y registrado, pero la OSE no respondió (`PENDIENTE_ENVIO`). Reintente con "
        "`POST .../envios`.\n"
        "* **200**: repetición idempotente (misma `Idempotency-Key` y mismo contenido)."
    ),
    responses={
        200: {"model": ComprobanteSalida, "description": "Repetición idempotente: se devuelve el comprobante ya "
                                                         "emitido, sin crear otro."},
        202: {"model": ComprobanteSalida, "description": "Registrado y firmado; OSE no disponible "
                                                         "(PENDIENTE_ENVIO)."},
        **respuestas(400, 401, 403, 409, 422),
    },
)
def emitir_comprobante(
    cuerpo: CuerpoComprobante,
    request: Request,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", min_length=8, max_length=100,
                                                  description="Evita duplicados si el cliente reintenta.")] = None,
) -> ComprobanteSalida:
    resultado = _contenedor(request).emitir_comprobante.ejecutar(comando_emision(cuerpo, idempotency_key))
    comprobante = resultado.comprobante
    if resultado.repetido:
        response.status_code = 200
    elif comprobante.estado is EstadoComprobante.PENDIENTE_ENVIO:
        response.status_code = 202
    response.headers["Location"] = ruta(comprobante)
    return comprobante_json(comprobante)


@router.get(
    "/{tipo_comprobante}/{serie_numero}",
    response_model=ComprobanteSalida,
    dependencies=[requiere("comprobantes:leer")],
    summary="Consulta un comprobante (vista JSON)",
    responses=respuestas(400, 401, 403, 404),
)
def consultar_comprobante(tipo_comprobante: TipoPath, serie_numero: SerieNumeroPath,
                          request: Request) -> ComprobanteSalida:
    return comprobante_json(_contenedor(request).consultar_comprobante.ejecutar(tipo_comprobante, serie_numero))


@router.get(
    "/{tipo_comprobante}/{serie_numero}/xml",
    response_class=Response,
    dependencies=[requiere("comprobantes:leer")],
    summary="Descarga el XML UBL 2.1 firmado (vista XML)",
    responses={200: {"content": {"application/xml": {}}, "description": "XML UBL 2.1 firmado."},
               **respuestas(400, 401, 403, 404)},
)
def descargar_xml(tipo_comprobante: TipoPath, serie_numero: SerieNumeroPath, request: Request) -> Response:
    return comprobante_xml(_contenedor(request).consultar_comprobante.ejecutar(tipo_comprobante, serie_numero))


@router.post(
    "/{tipo_comprobante}/{serie_numero}/envios",
    response_model=ComprobanteSalida,
    dependencies=[requiere("comprobantes:emitir")],
    summary="Reintenta el envío a la OSE de un comprobante PENDIENTE_ENVIO",
    responses=respuestas(400, 401, 403, 404, 409, 502, 503),
)
def reenviar_comprobante(tipo_comprobante: TipoPath, serie_numero: SerieNumeroPath,
                         request: Request) -> ComprobanteSalida:
    return comprobante_json(_contenedor(request).reenviar_comprobante.ejecutar(tipo_comprobante, serie_numero))
