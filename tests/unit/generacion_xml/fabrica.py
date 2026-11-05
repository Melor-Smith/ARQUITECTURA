"""Fábrica de comprobantes del dominio para las pruebas de generación del XML.

Las pruebas de generación parten SIEMPRE de objetos del dominio (``Comprobante``), no de
JSON ni de HTTP: así se verifica la traducción "lenguaje del dominio → UBL 2.1" de forma
aislada.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal as D

from lxml import etree

from src.adapters.outbound.persistencia.semillas import EMISOR_ABC
from src.adapters.outbound.ubl import NAMESPACES
from src.adapters.outbound.ubl.generador import GeneradorUblXsdata
from src.domain.catalogos import (
    AfectacionIGV,
    Moneda,
    MotivoNotaCredito,
    MotivoNotaDebito,
    SistemaISC,
    TipoComprobante,
    TipoDocumentoIdentidad,
    UnidadMedida,
)
from src.domain.comprobante import BorradorComprobante, Cdr, Cliente, Comprobante, Linea
from src.domain.pagos import Cuota, FormaPago, TipoFormaPago
from src.domain.tributos import ConfiguracionISC
from src.domain.valores import Correlativo, DocumentoIdentidad, Serie

HOY = dt.date(2026, 10, 22)
HORA = dt.time(10, 30, 0)
NS = {k: v for k, v in NAMESPACES.items() if k in ("cac", "cbc", "ext", "ds")}

CLIENTE_RUC = Cliente(DocumentoIdentidad(TipoDocumentoIdentidad.RUC, "20123456786"),
                      "DISTRIBUIDORA EL SOL & CIA S.A.C.", "JR. COMERCIO 123, LIMA")
CLIENTE_DNI = Cliente(DocumentoIdentidad(TipoDocumentoIdentidad.DNI, "46027897"), "MARÍA QUISPE HUAMÁN")
CLIENTE_EXTERIOR = Cliente(DocumentoIdentidad(TipoDocumentoIdentidad.NO_DOMICILIADO, "US-99887766"),
                           "GROCERY IMPORTS LLC")


def linea(numero: int, descripcion: str = "Arroz extra a granel", *, cantidad: str = "50", valor: str = "4.20",
          unidad: UnidadMedida = UnidadMedida.KILOGRAMO, afectacion: AfectacionIGV = AfectacionIGV.GRAVADO_ONEROSA,
          codigo: str | None = "AB-ARR-001", isc: ConfiguracionISC | None = None, icbper: bool = False) -> Linea:
    return Linea.calcular(numero=numero, codigo_producto=codigo, descripcion=descripcion, unidad=unidad,
                          cantidad=D(cantidad), valor_unitario=D(valor), afectacion=afectacion,
                          fecha_emision=HOY, isc=isc, aplica_icbper=icbper)


def armar(tipo: TipoComprobante, serie: str, lineas: tuple[Linea, ...], *, cliente: Cliente = CLIENTE_RUC,
          correlativo: int = 1, moneda: Moneda = Moneda.PEN, tipo_cambio: D | None = None,
          forma_pago: FormaPago | None = None, referencia: Comprobante | None = None, motivo=None,
          documentos_legado: tuple[str, ...] = ()) -> Comprobante:
    return BorradorComprobante.preparar(
        tipo=tipo, serie=Serie(serie), fecha_emision=HOY, hora_emision=HORA, hoy=HOY, plazo_dias=3,
        moneda=moneda, tipo_cambio=tipo_cambio, emisor=EMISOR_ABC, cliente=cliente, lineas=lineas,
        referencia=referencia, motivo=motivo, sustento="Sustento de la nota" if motivo else None,
        forma_pago=forma_pago, documentos_legado=documentos_legado,
    ).numerar(Correlativo(correlativo))


# --- escenarios de negocio --------------------------------------------------------------
def factura_contado() -> Comprobante:
    return armar(TipoComprobante.FACTURA, "F001", (linea(1),))


def factura_credito() -> Comprobante:
    # 50 kg x 4.20 = 210.00 + IGV 37.80 = 247.80, en dos cuotas.
    cuotas = (Cuota(D("123.90"), dt.date(2026, 11, 21)), Cuota(D("123.90"), dt.date(2026, 12, 21)))
    return armar(TipoComprobante.FACTURA, "F001", (linea(1),), forma_pago=FormaPago(TipoFormaPago.CREDITO, cuotas))


def factura_completa() -> Comprobante:
    """Una línea por cada caso tributario: gravado, ISC 01/02/03, ICBPER, exonerado e inafecto."""
    return armar(TipoComprobante.FACTURA, "FA01", (
        linea(1),
        linea(2, "Pisco quebranta 750 ml", cantidad="6", valor="45.00", unidad=UnidadMedida.UNIDAD,
              codigo="BB-PIS-001", isc=ConfiguracionISC(SistemaISC.AL_VALOR, tasa=D("0.20"))),
        linea(3, "Cerveza botella 620 ml", cantidad="12", valor="5.50", unidad=UnidadMedida.UNIDAD,
              codigo="BB-CER-001", isc=ConfiguracionISC(SistemaISC.MONTO_FIJO, monto_fijo=D("1.35"))),
        linea(4, "Gaseosa 3 L", cantidad="4", valor="9.00", unidad=UnidadMedida.UNIDAD, codigo="BB-GAS-001",
              isc=ConfiguracionISC(SistemaISC.PRECIO_VENTA_PUBLICO, tasa=D("0.17"), precio_venta_publico=D("12.50"))),
        linea(5, "Bolsa plástica", cantidad="3", valor="0.10", unidad=UnidadMedida.UNIDAD, codigo="EM-BOL-001",
              icbper=True),
        linea(6, "Libro escolar", cantidad="2", valor="30.00", unidad=UnidadMedida.UNIDAD, codigo=None,
              afectacion=AfectacionIGV.EXONERADO_ONEROSA),
        linea(7, "Flete interno", cantidad="1", valor="15.00", unidad=UnidadMedida.SERVICIO, codigo=None,
              afectacion=AfectacionIGV.INAFECTO_ONEROSA),
    ))


def factura_exportacion_usd() -> Comprobante:
    return armar(TipoComprobante.FACTURA, "F002", (
        linea(1, "Quinua blanca", cantidad="1000", valor="2.10", afectacion=AfectacionIGV.EXPORTACION, codigo=None),
    ), cliente=CLIENTE_EXTERIOR, moneda=Moneda.USD, tipo_cambio=D("3.750"))


def factura_de_vale() -> Comprobante:
    return armar(TipoComprobante.FACTURA, "F001", (linea(1, cantidad="250", valor="3.80", codigo="AB-AZU-001"),),
                 documentos_legado=("VALE-SALIDA-0042",))


def boleta() -> Comprobante:
    return armar(TipoComprobante.BOLETA, "B001", (
        linea(1, "Aceite vegetal botella 1 L", cantidad="2", valor="8.50", unidad=UnidadMedida.UNIDAD,
              codigo="AB-ACE-001"),
    ), cliente=CLIENTE_DNI)


def _aceptada(c: Comprobante) -> Comprobante:
    c.registrar_firma(b"<x/>", "d")
    c.registrar_cdr(Cdr("0", "aceptada", dt.datetime(2026, 10, 22, 11)))
    return c


def nota_credito() -> Comprobante:
    return armar(TipoComprobante.NOTA_CREDITO, "FC01", (linea(1, cantidad="10"),),
                 referencia=_aceptada(factura_contado()), motivo=MotivoNotaCredito.DEVOLUCION_ITEM)


def nota_debito() -> Comprobante:
    return armar(TipoComprobante.NOTA_DEBITO, "FD01", (
        linea(1, "Intereses moratorios", cantidad="1", valor="15.00", unidad=UnidadMedida.SERVICIO, codigo=None),
    ), referencia=_aceptada(factura_contado()), motivo=MotivoNotaDebito.INTERESES_MORA)


ESCENARIOS = {
    "factura-contado": factura_contado,
    "factura-credito": factura_credito,
    "factura-completa": factura_completa,
    "factura-exportacion-usd": factura_exportacion_usd,
    "factura-de-vale": factura_de_vale,
    "boleta": boleta,
    "nota-credito": nota_credito,
    "nota-debito": nota_debito,
}


# --- utilidades -------------------------------------------------------------------------
def generar(c: Comprobante) -> bytes:
    return GeneradorUblXsdata().generar(c)


def arbol(c: Comprobante) -> etree._Element:
    return etree.fromstring(generar(c))


def texto(raiz: etree._Element, xpath: str) -> str:
    nodos = raiz.xpath(xpath, namespaces=NS)
    assert nodos, f"No existe {xpath}"
    nodo = nodos[0]
    return nodo if isinstance(nodo, str) else nodo.text


def todos(raiz: etree._Element, xpath: str) -> list[str]:
    return [n if isinstance(n, str) else n.text for n in raiz.xpath(xpath, namespaces=NS)]
