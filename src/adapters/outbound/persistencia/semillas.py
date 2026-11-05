"""Datos maestros de ABC Software Corp para desarrollo y demostración.

Antes estos datos vivían en ``tests/mocks`` y el código de producción los importaba. Ahora
son datos de configuración del adaptador de persistencia y se inyectan desde
``src/bootstrap.py``. Las pruebas pueden inyectar otros.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from src.domain.catalogos import (
    SentidoMovimiento,
    TipoDocumentoPLE,
    TipoExistencia,
    TipoOperacionInventario,
    UnidadMedida,
)
from src.domain.comprobante import Emisor
from src.domain.inventario import DocumentoSoporte, Homologacion, Producto
from src.domain.valores import Ruc

EMISOR_ABC = Emisor(
    ruc=Ruc("20556677884"),  # dígito verificador módulo 11 correcto
    razon_social="ABC SOFTWARE CORP S.A.C.",
    nombre_comercial="ABC DISTRIBUCIONES",
    direccion="AV. INDUSTRIAL 450, LIMA",
    ubigeo="150101",
    codigo_establecimiento="0000",
)

PRODUCTOS: list[Producto] = [
    Producto("AB-ARR-001", "ARROZ EXTRA A GRANEL", UnidadMedida.KILOGRAMO),
    Producto("AB-AZU-001", "AZUCAR RUBIA A GRANEL", UnidadMedida.KILOGRAMO),
    Producto("AB-ACE-001", "ACEITE VEGETAL BOTELLA 1 L", UnidadMedida.UNIDAD),
    Producto("BB-CER-001", "CERVEZA BOTELLA 620 ML", UnidadMedida.UNIDAD),
    Producto("BB-PIS-001", "PISCO QUEBRANTA 750 ML", UnidadMedida.UNIDAD),
    Producto("BB-GAS-001", "GASEOSA 3 L", UnidadMedida.UNIDAD),
    Producto("EM-BOL-001", "BOLSA PLASTICA CON ASA", UnidadMedida.UNIDAD, TipoExistencia.ENVASES),
]

#: Tabla de homologación: glosa libre del sistema antiguo -> producto y factor de conversión.
HOMOLOGACIONES: list[Homologacion] = [
    Homologacion("Saco de Arroz Extra 50kg", "AB-ARR-001", Decimal("50")),
    Homologacion("Saco de Azúcar Rubia 50kg", "AB-AZU-001", Decimal("50")),
    Homologacion("Caja Aceite Vegetal 12x1L", "AB-ACE-001", Decimal("12")),
]

FECHA_SALDO_INICIAL = dt.date(2026, 10, 1)

SALDOS_INICIALES: dict[str, Decimal] = {
    "AB-ARR-001": Decimal("2000"),
    "AB-AZU-001": Decimal("1000"),
    "AB-ACE-001": Decimal("240"),
    "BB-CER-001": Decimal("600"),
    "BB-PIS-001": Decimal("120"),
    "BB-GAS-001": Decimal("300"),
    "EM-BOL-001": Decimal("5000"),
}


def cargar_saldos_iniciales(kardex_repo, ids, establecimiento: str = "0000",
                            fecha: dt.date = FECHA_SALDO_INICIAL) -> None:
    """Registra el inventario inicial (tabla 12, operación 16) de cada producto."""
    por_codigo = {p.codigo: p for p in PRODUCTOS}
    documento = DocumentoSoporte(TipoDocumentoPLE.OTROS, "INV", "1", fecha)
    for codigo, cantidad in SALDOS_INICIALES.items():
        kardex = kardex_repo.obtener(establecimiento, por_codigo[codigo])
        kardex.registrar(
            id_movimiento=ids.siguiente("MOV"), fecha=fecha, tipo_operacion=TipoOperacionInventario.SALDO_INICIAL,
            sentido=SentidoMovimiento.ENTRADA, cantidad=cantidad, documento=documento,
            glosa="Inventario inicial",
        )
        kardex_repo.guardar(kardex)
