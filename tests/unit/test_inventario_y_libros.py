"""Kardex, ficha del sistema antiguo, equivalencias de unidades y libros PLE 14.1 / 12.1."""

import datetime as dt
from decimal import Decimal as D

import pytest

from src.domain.catalogos import (
    SentidoMovimiento,
    TipoDocumentoPLE,
    TipoOperacionInventario,
    UnidadMedida,
    UnidadMedidaPLE,
)
from src.domain.errores import ErrorDominio, FichaLegadoInvalida, SaldoInsuficiente
from src.domain.inventario import DocumentoSoporte, FichaLegado, Homologacion, Kardex, Producto
from src.domain.libros import Periodo, inventario_121
from src.domain.valores import Ruc

ARROZ = Producto("AB-ARR-001", "ARROZ", UnidadMedida.KILOGRAMO)
DOC = DocumentoSoporte(TipoDocumentoPLE.OTROS, "INV", "1", dt.date(2026, 10, 1))
FACTURA = DocumentoSoporte(TipoDocumentoPLE.FACTURA, "F001", "1", dt.date(2026, 10, 5))


def kardex_con(saldo: str) -> Kardex:
    k = Kardex("0000", ARROZ)
    k.registrar(id_movimiento="M1", fecha=dt.date(2026, 10, 1), tipo_operacion=TipoOperacionInventario.SALDO_INICIAL,
                sentido=SentidoMovimiento.ENTRADA, cantidad=D(saldo), documento=DOC)
    return k


class TestKardex:
    def test_saldo_se_actualiza_con_cada_movimiento(self):
        k = kardex_con("100")
        m = k.registrar(id_movimiento="M2", fecha=dt.date(2026, 10, 5), tipo_operacion=TipoOperacionInventario.VENTA,
                        sentido=SentidoMovimiento.SALIDA, cantidad=D("30"), documento=FACTURA)
        assert (m.salida, m.saldo, k.saldo) == (D("30"), D("70"), D("70"))

    @pytest.mark.parametrize("operacion", [TipoOperacionInventario.VENTA, TipoOperacionInventario.DEVOLUCION_ENTREGADA])
    def test_venta_o_compra_con_documento_interno_se_rechaza(self, operacion):
        """Anexo 2, 12.1, campo 11: las operaciones 01 a 06 no admiten documento '00' (confirmado
        con el validador PLE 5.2.0.7: "Tipo de documento no válido para tipo de operación efectuada")."""
        with pytest.raises(ErrorDominio) as error:
            kardex_con("100").registrar(id_movimiento="M2", fecha=dt.date(2026, 10, 5), tipo_operacion=operacion,
                                        sentido=SentidoMovimiento.SALIDA, cantidad=D("1"), documento=DOC)
        assert error.value.codigo == "ERR-KARDEX-DOCUMENTO-OPERACION"

    def test_no_permite_saldo_negativo(self):
        with pytest.raises(SaldoInsuficiente):
            kardex_con("10").registrar(id_movimiento="M2", fecha=dt.date(2026, 10, 5),
                                       tipo_operacion=TipoOperacionInventario.VENTA,
                                       sentido=SentidoMovimiento.SALIDA, cantidad=D("11"), documento=DOC)

    def test_no_permite_movimientos_con_fecha_anterior(self):
        with pytest.raises(ErrorDominio, match="fecha anterior"):
            kardex_con("10").registrar(id_movimiento="M2", fecha=dt.date(2026, 9, 30),
                                       tipo_operacion=TipoOperacionInventario.COMPRA,
                                       sentido=SentidoMovimiento.ENTRADA, cantidad=D("1"), documento=DOC)

    def test_tipo_de_operacion_tabla_12_debe_coincidir_con_el_sentido(self):
        with pytest.raises(ErrorDominio, match="no admite"):
            kardex_con("10").verificar(fecha=dt.date(2026, 10, 5), tipo_operacion=TipoOperacionInventario.COMPRA,
                                       sentido=SentidoMovimiento.SALIDA, cantidad=D("1"))


class TestFichaLegado:
    def test_ficha_sin_movimiento(self):
        with pytest.raises(FichaLegadoInvalida) as e:
            FichaLegado(dt.date(2026, 10, 1), D("0"), D("0"), "Arroz", "VALE-1")
        assert e.value.codigo == "ERR-LEGADO-SIN-MOVIMIENTO"

    def test_ficha_con_ingreso_y_salida_a_la_vez(self):
        with pytest.raises(FichaLegadoInvalida) as e:
            FichaLegado(dt.date(2026, 10, 1), D("1"), D("2"), "Arroz", "VALE-1")
        assert e.value.codigo == "ERR-LEGADO-AMBIGUA"

    def test_vale_interno_es_documento_tipo_00_y_no_guia_de_remision_09(self):
        doc = DocumentoSoporte.desde_documento_interno("VALE-SALIDA-0042", dt.date(2026, 10, 15))
        assert doc.tipo is TipoDocumentoPLE.OTROS
        assert doc.tipo is not TipoDocumentoPLE.GUIA_REMISION_REMITENTE
        assert (doc.serie, doc.numero) == ("VALE-SALIDA", "0042")

    def test_homologacion_ignora_tildes_mayusculas_y_espacios(self):
        h = Homologacion("Saco de Azúcar Rubia 50kg", "AB-AZU-001", D("50"))
        assert h.clave == Homologacion("  saco de AZUCAR   rubia 50KG ", "x").clave


class TestClasificacionDocumentoLegado:
    @pytest.mark.parametrize(("texto", "regla", "tipo", "serie", "numero"), [
        ("VALE-SALIDA-0042", "DOCUMENTO_INTERNO", "00", "VALE-SALIDA", "0042"),
        ("GUIA-INT-0015", "DOCUMENTO_INTERNO", "00", "GUIA-INT", "0015"),
        ("F001-00004587", "COMPROBANTE_ELECTRONICO", "01", "F001", "4587"),
        ("B001-0000231", "COMPROBANTE_ELECTRONICO", "03", "B001", "231"),
        ("FACT 001-4587", "FACTURA_FISICA", "01", "0001", "4587"),
        ("factura nro 12-345", "NO_RECONOCIDO", "00", "FACTURA NRO 12", "345"),
        ("BOL. 2-15", "BOLETA_FISICA", "03", "0002", "15"),
        ("GUIA 0002-781", "GUIA_REMISION", "09", "0002", "781"),
        ("GR EG01-55", "GUIA_REMISION", "09", "EG01", "55"),
        ("S/N", "SIN_DOCUMENTO", "00", "SN", "20261015"),
        ("pedido de Juan", "DOCUMENTO_INTERNO", "00", "0", "PEDIDO DE JUAN"),
        ("xyz", "NO_RECONOCIDO", "00", "0", "XYZ"),
    ])
    def test_reconoce_el_documento_real(self, texto, regla, tipo, serie, numero):
        from src.domain.inventario import clasificar_documento_legado

        resultado = clasificar_documento_legado(texto, dt.date(2026, 10, 15))
        d = resultado.documento
        assert (resultado.regla, d.tipo.value, d.serie, d.numero) == (regla, tipo, serie, numero)
        assert (resultado.observacion is not None) == (regla in ("SIN_DOCUMENTO", "NO_RECONOCIDO"))

    @pytest.mark.parametrize("texto", ["2026-10-15", "15/10/2026", "15-10-2026", "15.10.2026", "15/10/26"])
    def test_formatos_de_fecha(self, texto):
        from src.domain.inventario import parsear_fecha_legado

        assert parsear_fecha_legado(texto) == dt.date(2026, 10, 15)

    @pytest.mark.parametrize("texto", ["31/09/2026", "2026/10/15", "ayer", "15-oct-2026"])
    def test_fechas_invalidas(self, texto):
        from src.domain.inventario import parsear_fecha_legado

        with pytest.raises(FichaLegadoInvalida) as e:
            parsear_fecha_legado(texto)
        assert e.value.codigo == "ERR-LEGADO-FECHA"


class TestEquivalenciaUnidades:
    @pytest.mark.parametrize(("unece", "tabla6"), [
        (UnidadMedida.KILOGRAMO, UnidadMedidaPLE.KILOGRAMOS),
        (UnidadMedida.UNIDAD, UnidadMedidaPLE.UNIDADES),
        (UnidadMedida.LITRO, UnidadMedidaPLE.LITROS),
        (UnidadMedida.CAJA, UnidadMedidaPLE.CAJAS),
        (UnidadMedida.SERVICIO, UnidadMedidaPLE.OTROS),
        (UnidadMedida.SACO, UnidadMedidaPLE.OTROS),
    ])
    def test_catalogo_03_unece_a_tabla_6_ple(self, unece, tabla6):
        assert unece.unidad_ple is tabla6


class TestLibros:
    def test_periodo(self):
        assert Periodo.parsear("202610").codigo_ple == "20261000"
        with pytest.raises(ErrorDominio):
            Periodo.parsear("202613")

    def test_inventario_121_usa_tabla_6_y_respeta_el_periodo(self):
        k = kardex_con("100")
        libro = inventario_121(Ruc("20556677884"), Periodo(2026, 10), k.movimientos)
        fila = libro.filas[0]
        # campo 16 en UN/ECE: el PLE 5.2.0.7 rechaza los códigos numéricos de la tabla 6 anterior
        assert (fila.unidad_medida, fila.tipo_operacion, fila.tipo_documento) == ("KGM", "16", "00")
        assert libro.nombre_archivo == "LE2055667788420261000120100001111.txt"
        assert inventario_121(Ruc("20556677884"), Periodo(2026, 11), k.movimientos).nombre_archivo.endswith(
            "120100001011.txt")  # posición 30 "1" empresa operativa; posición 31 "0" sin información
