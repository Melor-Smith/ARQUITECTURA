"""Caso de uso del Taller 2: de una venta registrada en el formulario al XML UBL 2.1.

Usa las mismas reglas del dominio que la emisión (``Linea``, ``Totales``, ``BorradorComprobante``)
y los mismos puertos de generación y validación del XSD, pero se detiene en el XML:

* no registra el comprobante, no mueve el Kardex y no lo envía a la OSE. El XML se valida
  afuera, en el OSE-DEMO de Nubefact (``docs/evidencia-nubefact``);
* el producto es texto libre: no tiene que existir en el catálogo de ABC;
* el correlativo lo sigue asignando la secuencia del servidor después de validar, nunca el usuario.

**Sin firma por defecto.** Se omite ``ext:UBLExtensions`` completo, que en el XSD es opcional
(0..1). No se deja un ``ext:ExtensionContent`` vacío porque el XSD exige su contenido. La firma
XMLDSig es opcional (``incluir_firma``) y, si se pide, el XML firmado se vuelve a validar.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from src.application.comandos import GenerarXmlVentaCmd, LineaCmd
from src.application.puertos import FirmaDigital, GeneradorUBL, Reloj, SecuenciaCorrelativos, ValidadorEsquemaUBL
from src.domain.catalogos import Moneda, TipoComprobante
from src.domain.comprobante import BorradorComprobante, Cliente, Comprobante, Emisor, Linea
from src.domain.errores import ReglaComprobanteIncumplida
from src.domain.tributos import ConfiguracionISC
from src.domain.valores import DocumentoIdentidad, Serie

TIPOS_DE_VENTA = (TipoComprobante.FACTURA, TipoComprobante.BOLETA)


@dataclass(frozen=True, slots=True)
class XmlDeVenta:
    comprobante: Comprobante
    xml: bytes
    firmado: bool

    @property
    def nombre_archivo(self) -> str:
        """Nombre SUNAT: ``RUC-TIPO-SERIE-NUMERO.xml``."""
        return f"{self.comprobante.nombre_archivo}.xml"


class GenerarXmlVenta:
    def __init__(
        self,
        *,
        emisor: Emisor,
        plazo_envio_dias: int,
        reloj: Reloj,
        secuencia: SecuenciaCorrelativos,
        generador_ubl: GeneradorUBL,
        validador_xsd: ValidadorEsquemaUBL,
        firma: FirmaDigital,
    ) -> None:
        self._emisor = emisor
        self._plazo = plazo_envio_dias
        self._reloj = reloj
        self._secuencia = secuencia
        self._generador = generador_ubl
        self._validador = validador_xsd
        self._firma = firma

    def ejecutar(self, cmd: GenerarXmlVentaCmd) -> XmlDeVenta:
        if cmd.tipo not in TIPOS_DE_VENTA:
            raise ReglaComprobanteIncumplida(
                "El formulario de venta genera facturas (01) o boletas (03); las notas se emiten por la API.",
                campo="tipo_comprobante",
            )
        ahora = self._reloj.ahora()
        hoy = ahora.date()
        borrador = BorradorComprobante.preparar(
            tipo=cmd.tipo,
            serie=Serie(cmd.serie.strip().upper()),
            fecha_emision=hoy,
            hora_emision=ahora.time().replace(microsecond=0),
            hoy=hoy,
            plazo_dias=self._plazo,
            moneda=Moneda.PEN,
            tipo_cambio=None,
            emisor=self._emisor,
            cliente=Cliente(
                DocumentoIdentidad(cmd.cliente.tipo_documento, cmd.cliente.numero_documento.strip().upper()),
                cmd.cliente.nombre.strip(),
                (cmd.cliente.direccion or "").strip() or None,
            ),
            lineas=tuple(self._linea(i, ln, ahora) for i, ln in enumerate(cmd.lineas, start=1)),
        )
        # Todas las reglas pasaron: recién ahora se consume un correlativo.
        comprobante = borrador.numerar(self._secuencia.siguiente(self._emisor.ruc, cmd.tipo, borrador.serie))
        xml = self._generador.generar(comprobante)
        self._validador.validar(xml, comprobante.tipo)
        if not cmd.incluir_firma:
            return XmlDeVenta(comprobante, xml, firmado=False)
        firmado = self._firma.firmar(xml)
        self._validador.validar(firmado.xml, comprobante.tipo)
        return XmlDeVenta(comprobante, firmado.xml, firmado=True)

    @staticmethod
    def _linea(numero: int, cmd: LineaCmd, ahora: dt.datetime) -> Linea:
        isc = None
        if cmd.isc is not None:
            isc = ConfiguracionISC(cmd.isc.sistema, cmd.isc.tasa, cmd.isc.monto_fijo, cmd.isc.precio_venta_publico)
        return Linea.calcular(
            numero=numero, descripcion=cmd.descripcion, unidad=cmd.unidad_medida, cantidad=cmd.cantidad,
            valor_unitario=cmd.valor_unitario, afectacion=cmd.afectacion_igv, fecha_emision=ahora.date(),
            isc=isc, aplica_icbper=cmd.aplica_icbper,
        )
