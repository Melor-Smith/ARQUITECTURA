"""Vista (la V de MVC): representaciones de un ``Comprobante``.

* JSON (``ComprobanteSalida``), para sistemas cliente.
* XML UBL 2.1 firmado (``application/xml``), el documento tributario.

La vista NO es el contrato OpenAPI: el contrato describe estas representaciones.
"""

from __future__ import annotations

from fastapi.responses import Response

from src.adapters.inbound.http.esquemas import (
    CdrSalida,
    CodigoDescripcion,
    ComprobanteSalida,
    CuotaSalida,
    EnlacesComprobante,
    FormaPagoSalida,
    IscLinea,
    LineaSalida,
    ParteSalida,
    ReferenciaSalida,
    TotalesSalida,
    TributoLinea,
)
from src.domain.comprobante import Comprobante

PREFIJO = "/api/v1/comprobantes"


def _cd(enum) -> CodigoDescripcion:
    return CodigoDescripcion(codigo=enum.value, descripcion=enum.descripcion)


def ruta(comprobante: Comprobante) -> str:
    return f"{PREFIJO}/{comprobante.tipo.value}/{comprobante.serie_numero}"


def comprobante_json(c: Comprobante) -> ComprobanteSalida:
    base = ruta(c)
    t = c.totales
    return ComprobanteSalida(
        tipo_comprobante=_cd(c.tipo),
        serie=str(c.numero.serie),
        correlativo=c.numero.correlativo.valor,
        serie_numero=c.serie_numero,
        fecha_emision=c.fecha_emision,
        hora_emision=c.hora_emision,
        moneda=c.moneda.value,
        tipo_cambio=c.tipo_cambio,
        emisor=ParteSalida(tipo_documento="6", numero_documento=str(c.emisor.ruc), nombre=c.emisor.razon_social),
        cliente=ParteSalida(tipo_documento=c.cliente.documento.tipo.value,
                            numero_documento=c.cliente.documento.numero, nombre=c.cliente.nombre),
        lineas=[
            LineaSalida(
                numero=ln.numero,
                codigo_producto=ln.codigo_producto,
                descripcion=ln.descripcion,
                unidad_medida=ln.unidad.value,
                cantidad=ln.cantidad,
                valor_unitario=ln.valor_unitario,
                precio_unitario=ln.precio_unitario,
                valor_venta=ln.valor_venta,
                afectacion_igv=_cd(ln.afectacion),
                isc=IscLinea(sistema=_cd(ln.isc.sistema), base=ln.base_isc, monto=ln.monto_isc) if ln.isc else None,
                igv=TributoLinea(base=ln.base_igv, monto=ln.monto_igv),
                icbper=ln.monto_icbper,
            )
            for ln in c.lineas
        ],
        totales=TotalesSalida(
            gravadas=t.gravadas, exoneradas=t.exoneradas, inafectas=t.inafectas, exportacion=t.exportacion,
            isc=t.isc, igv=t.igv, icbper=t.icbper, total_impuestos=t.total_impuestos, valor_venta=t.valor_venta,
            importe_total=t.importe_total,
        ),
        monto_en_letras=c.monto_en_letras,
        forma_pago=FormaPagoSalida(
            tipo=c.forma_pago.tipo.name,
            monto_pendiente=c.forma_pago.monto_pendiente,
            cuotas=[CuotaSalida(numero=n, monto=q.monto, fecha_vencimiento=q.fecha_vencimiento)
                    for n, q in enumerate(c.forma_pago.cuotas, start=1)],
        ) if c.forma_pago else None,
        documentos_legado=list(c.documentos_legado),
        referencia=(ReferenciaSalida(tipo_comprobante=c.referencia.tipo.value, serie_numero=c.referencia.serie_numero)
                    if c.referencia else None),
        motivo=_cd(c.motivo) if c.motivo else None,
        sustento=c.sustento,
        estado=c.estado,
        hash_cpe=c.hash_cpe,
        cdr=(CdrSalida(codigo=c.cdr.codigo, descripcion=c.cdr.descripcion, observaciones=list(c.cdr.observaciones),
                       fecha_recepcion=c.cdr.fecha_recepcion) if c.cdr else None),
        intentos_envio=c.intentos_envio,
        enlaces=EnlacesComprobante(detalle=base, xml=f"{base}/xml", envios=f"{base}/envios"),
    )


def comprobante_xml(c: Comprobante) -> Response:
    return Response(
        content=c.xml_firmado or b"",
        media_type="application/xml",
        headers={"Content-Disposition": f'inline; filename="{c.nombre_archivo}.xml"'},
    )
