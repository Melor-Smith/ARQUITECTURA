"""Controlador web (la C de MVC) del formulario "Registrar venta" del Taller 2.

* ``GET /venta`` muestra el formulario con el caso de estudio (una motocicleta) y una serie nueva.
* ``POST /venta`` traduce los campos al comando, ejecuta ``GenerarXmlVenta`` y vuelve a mostrar la
  página con el XML, los importes y la matriz, o con el error marcado en su campo.

No forma parte de la API REST ``/api/v1``: es una vista HTML para personas y no figura en el OpenAPI
(contrato del ADR 0013). No registra, no envía y no modifica el inventario; solo genera y valida el
XML, como el caso de uso que la respalda.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.adapters.inbound.http.formulario_venta import MAXIMO_BYTES, ErrorFormulario, FormularioVenta
from src.adapters.inbound.http.vistas.matriz_ubl import filas_aplicadas
from src.adapters.inbound.http.vistas.venta import CABECERAS_SEGURIDAD, Aviso, pagina_venta
from src.application.errores import XmlNoConformeXsd
from src.bootstrap import Contenedor
from src.domain.errores import ErrorDominio

router = APIRouter(include_in_schema=False)


def _html(contenido: str, estado: int = 200) -> HTMLResponse:
    return HTMLResponse(contenido, status_code=estado, headers=CABECERAS_SEGURIDAD)


def _emisor(contenedor: Contenedor) -> str:
    return f"{contenedor.emisor.nombre_comercial} · RUC {contenedor.emisor.ruc}"


@router.get("/")
def inicio() -> RedirectResponse:
    return RedirectResponse("/venta", status_code=307)


@router.get("/venta", response_class=HTMLResponse)
def formulario(request: Request) -> HTMLResponse:
    contenedor: Contenedor = request.app.state.contenedor
    return _html(pagina_venta(FormularioVenta.caso_de_estudio(), emisor=_emisor(contenedor)))


@router.post("/venta", response_class=HTMLResponse)
async def generar_xml(request: Request) -> HTMLResponse:
    contenedor: Contenedor = request.app.state.contenedor
    emisor = _emisor(contenedor)
    cuerpo = await request.body()
    if len(cuerpo) > MAXIMO_BYTES:
        aviso = Aviso("La venta supera el tamaño máximo del formulario.", ErrorFormulario.codigo)
        return _html(pagina_venta(FormularioVenta.caso_de_estudio(), aviso=aviso, emisor=emisor), 413)

    formulario = FormularioVenta.desde_cuerpo(cuerpo.decode("utf-8", errors="replace"))
    try:
        resultado = contenedor.generar_xml_venta.ejecutar(formulario.comando())
    except ErrorFormulario as exc:
        return _html(pagina_venta(formulario, aviso=Aviso(exc.mensaje, exc.codigo, exc.campo), emisor=emisor), 400)
    except ErrorDominio as exc:
        return _html(pagina_venta(formulario, aviso=Aviso(exc.mensaje, exc.codigo, exc.campo), emisor=emisor), 422)
    except XmlNoConformeXsd as exc:  # defecto interno: nunca se entrega un XML que no valida
        aviso = Aviso(exc.mensaje, exc.codigo, detalles=tuple(exc.errores[:5]))
        return _html(pagina_venta(formulario, aviso=aviso, emisor=emisor), 500)
    return _html(pagina_venta(formulario, resultado=resultado, filas=filas_aplicadas(resultado.xml), emisor=emisor))
