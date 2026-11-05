"""Catálogos SUNAT y tablas PLE usados por el dominio.

Cada enumeración usa como ``value`` el código oficial, de modo que el código viaja
igual por el JSON, el XML UBL y el TXT del PLE. Solo se incluyen los códigos que el
sistema soporta: un código fuera de la lista se rechaza en el contrato (HTTP 400).

Fuentes:
* Anexo 8 de la RS 097-2012/SUNAT y modificatorias (catálogos 01, 02, 03, 05, 06, 07,
  08, 09, 10, 12 y 51).
* Anexo 3 de la RS 286-2009/SUNAT (tablas 2, 4, 5, 6, 10, 12 y 13 del PLE).
"""

from __future__ import annotations

from enum import Enum


class _EnumConDescripcion(str, Enum):
    """Enum cuyo valor es el código oficial y que además lleva una descripción."""

    def __new__(cls, codigo: str, descripcion: str):
        obj = str.__new__(cls, codigo)
        obj._value_ = codigo
        obj.descripcion = descripcion
        return obj

    def __str__(self) -> str:
        return self.value


class TipoComprobante(_EnumConDescripcion):
    """Catálogo 01 (y tabla 10 del PLE para estos mismos códigos)."""

    FACTURA = ("01", "Factura")
    BOLETA = ("03", "Boleta de venta")
    NOTA_CREDITO = ("07", "Nota de crédito")
    NOTA_DEBITO = ("08", "Nota de débito")

    @property
    def es_nota(self) -> bool:
        return self in (TipoComprobante.NOTA_CREDITO, TipoComprobante.NOTA_DEBITO)


class TipoOperacionSunat(_EnumConDescripcion):
    """Catálogo 51: tipo de operación (atributo ``listID`` de ``cbc:InvoiceTypeCode``)."""

    VENTA_INTERNA = ("0101", "Venta interna")
    EXPORTACION_BIENES = ("0200", "Exportación de bienes")


class TipoDocumentoIdentidad(_EnumConDescripcion):
    """Catálogo 06 (equivale a la tabla 2 del PLE)."""

    NO_DOMICILIADO = ("0", "Doc. tributario no domiciliado sin RUC / varios")
    DNI = ("1", "DNI")
    CARNET_EXTRANJERIA = ("4", "Carnet de extranjería")
    RUC = ("6", "RUC")
    PASAPORTE = ("7", "Pasaporte")
    CEDULA_DIPLOMATICA = ("A", "Cédula diplomática de identidad")


class Moneda(_EnumConDescripcion):
    """Catálogo 02 / tabla 4 del PLE (ISO 4217)."""

    PEN = ("PEN", "Soles")
    USD = ("USD", "Dólar estadounidense")


class Tributo(_EnumConDescripcion):
    """Catálogo 05: código de tributo, con su nombre, código internacional y categoría."""

    IGV = ("1000", "IGV")
    ISC = ("2000", "ISC")
    ICBPER = ("7152", "ICBPER")
    EXPORTACION = ("9995", "EXP")
    EXONERADO = ("9997", "EXO")
    INAFECTO = ("9998", "INA")

    @property
    def nombre(self) -> str:
        return self.descripcion

    @property
    def codigo_internacional(self) -> str:
        return {
            Tributo.IGV: "VAT",
            Tributo.ISC: "EXC",
            Tributo.ICBPER: "OTH",
            Tributo.EXPORTACION: "FRE",
            Tributo.EXONERADO: "VAT",
            Tributo.INAFECTO: "FRE",
        }[self]

    @property
    def categoria(self) -> str:
        """Código de categoría de tributo (UN/ECE 5305) usado en ``cac:TaxCategory/cbc:ID``."""
        return {
            Tributo.IGV: "S",
            Tributo.ISC: "S",
            Tributo.ICBPER: "S",
            Tributo.EXPORTACION: "G",
            Tributo.EXONERADO: "E",
            Tributo.INAFECTO: "O",
        }[self]


class AfectacionIGV(_EnumConDescripcion):
    """Catálogo 07. Se serializa en ``cac:TaxCategory/cbc:TaxExemptionReasonCode``."""

    GRAVADO_ONEROSA = ("10", "Gravado - Operación onerosa")
    EXONERADO_ONEROSA = ("20", "Exonerado - Operación onerosa")
    INAFECTO_ONEROSA = ("30", "Inafecto - Operación onerosa")
    EXPORTACION = ("40", "Exportación de bienes o servicios")

    @property
    def tributo(self) -> Tributo:
        return {
            AfectacionIGV.GRAVADO_ONEROSA: Tributo.IGV,
            AfectacionIGV.EXONERADO_ONEROSA: Tributo.EXONERADO,
            AfectacionIGV.INAFECTO_ONEROSA: Tributo.INAFECTO,
            AfectacionIGV.EXPORTACION: Tributo.EXPORTACION,
        }[self]

    @property
    def es_gravada(self) -> bool:
        return self is AfectacionIGV.GRAVADO_ONEROSA


class SistemaISC(_EnumConDescripcion):
    """Catálogo 08. Se serializa en ``cac:TaxCategory/cbc:TierRange``."""

    AL_VALOR = ("01", "Sistema al valor")
    MONTO_FIJO = ("02", "Aplicación del monto fijo")
    PRECIO_VENTA_PUBLICO = ("03", "Sistema de precios de venta al público")


class UnidadMedidaPLE(_EnumConDescripcion):
    """Tabla 6 del PLE: unidad de medida que exigen los libros 12.1 y 13.1 (no es UNECE)."""

    KILOGRAMOS = ("01", "Kilogramos")
    LIBRAS = ("02", "Libras")
    TONELADAS_METRICAS = ("04", "Toneladas métricas")
    GRAMOS = ("06", "Gramos")
    UNIDADES = ("07", "Unidades")
    LITROS = ("08", "Litros")
    GALONES = ("09", "Galones")
    BARRILES = ("10", "Barriles")
    LATAS = ("11", "Latas")
    CAJAS = ("12", "Cajas")
    MILLARES = ("13", "Millares")
    METROS_CUBICOS = ("14", "Metros cúbicos")
    METROS = ("15", "Metros")
    OTROS = ("99", "Otros")


class UnidadMedida(_EnumConDescripcion):
    """Catálogo 03 (UN/ECE Recomendación 20). Va en el atributo ``unitCode`` de la cantidad."""

    UNIDAD = ("NIU", "Unidad (bienes)")
    SERVICIO = ("ZZ", "Unidad (servicios)")
    KILOGRAMO = ("KGM", "Kilogramo")
    GRAMO = ("GRM", "Gramo")
    TONELADA = ("TNE", "Tonelada métrica")
    LIBRA = ("LBR", "Libra")
    LITRO = ("LTR", "Litro")
    MILILITRO = ("MLT", "Mililitro")
    GALON = ("GLL", "Galón (EE. UU.)")
    METRO = ("MTR", "Metro")
    METRO_CUBICO = ("MTQ", "Metro cúbico")
    CAJA = ("BX", "Caja")
    BOLSA = ("BG", "Bolsa")
    BOTELLA = ("BO", "Botella")
    LATA = ("CA", "Lata")
    PAQUETE = ("PK", "Paquete")
    SACO = ("SA", "Saco")
    DOCENA = ("DZN", "Docena")
    MILLAR = ("MIL", "Millar")
    BARRIL = ("BLL", "Barril")

    @property
    def unidad_ple(self) -> UnidadMedidaPLE:
        """Equivalencia Catálogo 03 (UNECE) → códigos numéricos de la tabla 6 anterior (01, 07…).

        Se conserva como referencia histórica y para el formato impreso. **No va en el TXT**:
        el validador PLE 5.2.0.7 rechaza esos códigos en el campo 16 del 12.1 ("El valor no se
        encontró en la tabla de parámetros") y acepta el código UN/ECE (KGM, NIU…).
        """
        return _UNECE_A_TABLA6.get(self, UnidadMedidaPLE.OTROS)


_UNECE_A_TABLA6: dict[UnidadMedida, UnidadMedidaPLE] = {
    UnidadMedida.KILOGRAMO: UnidadMedidaPLE.KILOGRAMOS,
    UnidadMedida.LIBRA: UnidadMedidaPLE.LIBRAS,
    UnidadMedida.TONELADA: UnidadMedidaPLE.TONELADAS_METRICAS,
    UnidadMedida.GRAMO: UnidadMedidaPLE.GRAMOS,
    UnidadMedida.UNIDAD: UnidadMedidaPLE.UNIDADES,
    UnidadMedida.LITRO: UnidadMedidaPLE.LITROS,
    UnidadMedida.GALON: UnidadMedidaPLE.GALONES,
    UnidadMedida.BARRIL: UnidadMedidaPLE.BARRILES,
    UnidadMedida.LATA: UnidadMedidaPLE.LATAS,
    UnidadMedida.CAJA: UnidadMedidaPLE.CAJAS,
    UnidadMedida.MILLAR: UnidadMedidaPLE.MILLARES,
    UnidadMedida.METRO_CUBICO: UnidadMedidaPLE.METROS_CUBICOS,
    UnidadMedida.METRO: UnidadMedidaPLE.METROS,
}


class MotivoNotaCredito(_EnumConDescripcion):
    """Catálogo 09."""

    ANULACION_OPERACION = ("01", "Anulación de la operación")
    ANULACION_ERROR_RUC = ("02", "Anulación por error en el RUC")
    CORRECCION_DESCRIPCION = ("03", "Corrección por error en la descripción")
    DESCUENTO_GLOBAL = ("04", "Descuento global")
    DESCUENTO_ITEM = ("05", "Descuento por ítem")
    DEVOLUCION_TOTAL = ("06", "Devolución total")
    DEVOLUCION_ITEM = ("07", "Devolución por ítem")
    BONIFICACION = ("08", "Bonificación")
    DISMINUCION_VALOR = ("09", "Disminución en el valor")
    OTROS_CONCEPTOS = ("10", "Otros conceptos")

    @property
    def es_devolucion(self) -> bool:
        return self in (MotivoNotaCredito.DEVOLUCION_TOTAL, MotivoNotaCredito.DEVOLUCION_ITEM)


class MotivoNotaDebito(_EnumConDescripcion):
    """Catálogo 10."""

    INTERESES_MORA = ("01", "Intereses por mora")
    AUMENTO_VALOR = ("02", "Aumento en el valor")
    PENALIDADES = ("03", "Penalidades / otros conceptos")


class TipoDocumentoRelacionado(_EnumConDescripcion):
    """Catálogo 12: documentos relacionados (``cac:AdditionalDocumentReference``)."""

    OTROS = ("99", "Otros")


class TipoDocumentoPLE(_EnumConDescripcion):
    """Tabla 10 del PLE: tipo del documento que sustenta el movimiento de inventario."""

    OTROS = ("00", "Otros (documento interno)")
    FACTURA = ("01", "Factura")
    BOLETA = ("03", "Boleta de venta")
    NOTA_CREDITO = ("07", "Nota de crédito")
    NOTA_DEBITO = ("08", "Nota de débito")
    GUIA_REMISION_REMITENTE = ("09", "Guía de remisión - remitente")

    @classmethod
    def desde_comprobante(cls, tipo: TipoComprobante) -> TipoDocumentoPLE:
        return cls(tipo.value)


class TipoExistencia(_EnumConDescripcion):
    """Tabla 5 del PLE."""

    MERCADERIAS = ("01", "Mercaderías")
    PRODUCTOS_TERMINADOS = ("02", "Productos terminados")
    MATERIAS_PRIMAS = ("03", "Materias primas")
    ENVASES = ("04", "Envases")
    MATERIALES_AUXILIARES = ("05", "Materiales auxiliares")
    SUMINISTROS = ("06", "Suministros")
    REPUESTOS = ("07", "Repuestos")
    EMBALAJES = ("08", "Embalajes")
    OTROS = ("99", "Otros")


class SentidoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


class TipoOperacionInventario(_EnumConDescripcion):
    """Tabla 12 del PLE (subconjunto usado por ABC Software Corp)."""

    VENTA = ("01", "Venta")
    COMPRA = ("02", "Compra")
    DEVOLUCION_ENTREGADA = ("06", "Devolución entregada")
    TRANSFERENCIA_ENTRE_ALMACENES = ("11", "Transferencia entre almacenes")
    MERMAS = ("13", "Mermas")
    SALDO_INICIAL = ("16", "Saldo inicial")
    ENTRADA_TRANSFERENCIA = ("21", "Entrada por transferencia entre almacenes")
    ENTRADA_DEVOLUCION_CLIENTE = ("24", "Entrada por devolución del cliente")
    OTROS = ("99", "Otros")

    @property
    def exige_comprobante(self) -> bool:
        """Anexo 2, formato 12.1, campo 11: si la operación es 01 a 06 (venta, compra,
        consignación, devolución…), el documento no puede ser '00' (interno): debe ser un
        comprobante de pago o una guía de remisión. Lo confirmó el validador PLE 5.2.0.7."""
        return self.value in {"01", "02", "03", "04", "05", "06"}

    @property
    def sentidos_permitidos(self) -> frozenset[SentidoMovimiento]:
        entrada = frozenset({SentidoMovimiento.ENTRADA})
        salida = frozenset({SentidoMovimiento.SALIDA})
        return {
            TipoOperacionInventario.VENTA: salida,
            TipoOperacionInventario.COMPRA: entrada,
            TipoOperacionInventario.DEVOLUCION_ENTREGADA: salida,
            TipoOperacionInventario.TRANSFERENCIA_ENTRE_ALMACENES: salida,
            TipoOperacionInventario.MERMAS: salida,
            TipoOperacionInventario.SALDO_INICIAL: entrada,
            TipoOperacionInventario.ENTRADA_TRANSFERENCIA: entrada,
            TipoOperacionInventario.ENTRADA_DEVOLUCION_CLIENTE: entrada,
            TipoOperacionInventario.OTROS: entrada | salida,
        }[self]


class CatalogoExistencias(_EnumConDescripcion):
    """Tabla 13 del PLE: catálogo de existencias utilizado."""

    OTROS = ("9", "Otros (catálogo propio)")
