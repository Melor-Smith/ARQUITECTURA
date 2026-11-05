"""Traducción del contrato (DTO) a comandos de la aplicación, compartida por los adaptadores de entrada.

La usan el adaptador HTTP y la línea de comandos: el mismo JSON produce el mismo comando,
venga por la red o desde un archivo.
"""

from __future__ import annotations

import hashlib
from typing import Annotated

from pydantic import Field, TypeAdapter

from src.adapters.inbound.http.esquemas import BoletaEntrada, FacturaEntrada, NotaCreditoEntrada, NotaDebitoEntrada
from src.application.comandos import (
    ClienteCmd,
    CuotaCmd,
    EmitirComprobanteCmd,
    FormaPagoCmd,
    IscCmd,
    LineaCmd,
    ReferenciaCmd,
)
from src.domain.catalogos import TipoComprobante
from src.domain.pagos import TipoFormaPago

ComprobanteEntrada = FacturaEntrada | BoletaEntrada | NotaCreditoEntrada | NotaDebitoEntrada
LECTOR_COMPROBANTE: TypeAdapter = TypeAdapter(
    Annotated[ComprobanteEntrada, Field(discriminator="tipo_comprobante")]
)


def comando_emision(cuerpo: ComprobanteEntrada, clave_idempotencia: str | None = None) -> EmitirComprobanteCmd:
    referencia = getattr(cuerpo, "referencia", None)
    return EmitirComprobanteCmd(
        tipo=TipoComprobante(cuerpo.tipo_comprobante),
        serie=cuerpo.serie,
        cliente=ClienteCmd(cuerpo.cliente.tipo_documento, cuerpo.cliente.numero_documento, cuerpo.cliente.nombre,
                           cuerpo.cliente.direccion),
        lineas=tuple(
            LineaCmd(
                descripcion=ln.descripcion, unidad_medida=ln.unidad_medida, cantidad=ln.cantidad,
                valor_unitario=ln.valor_unitario, afectacion_igv=ln.afectacion_igv,
                codigo_producto=ln.codigo_producto, aplica_icbper=ln.aplica_icbper,
                isc=IscCmd(ln.isc.sistema, ln.isc.tasa, ln.isc.monto_fijo, ln.isc.precio_venta_publico)
                if ln.isc else None,
            )
            for ln in cuerpo.lineas
        ),
        moneda=cuerpo.moneda,
        tipo_cambio=cuerpo.tipo_cambio,
        fecha_emision=cuerpo.fecha_emision,
        documentos_legado=tuple(getattr(cuerpo, "documentos_legado", ())),
        referencia=ReferenciaCmd(TipoComprobante(referencia.tipo_comprobante), referencia.serie_numero)
        if referencia else None,
        motivo=getattr(cuerpo, "motivo", None),
        sustento=getattr(cuerpo, "sustento", None),
        forma_pago=FormaPagoCmd(
            TipoFormaPago[cuerpo.forma_pago.tipo],
            tuple(CuotaCmd(c.monto, c.fecha_vencimiento) for c in cuerpo.forma_pago.cuotas),
        ) if isinstance(cuerpo, FacturaEntrada) else None,
        clave_idempotencia=clave_idempotencia,
        huella=hashlib.sha256(cuerpo.model_dump_json().encode()).hexdigest() if clave_idempotencia else None,
    )
