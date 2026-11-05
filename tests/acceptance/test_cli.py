"""Aceptación del adaptador de línea de comandos (Taller 2)."""

from lxml import etree

from src.adapters.inbound.cli import main
from src.adapters.outbound.ubl.validador import ValidadorXsdLxml
from src.domain.catalogos import TipoComprobante
from tests.conftest import EJEMPLOS


def test_genera_xml_firmados_y_validos_desde_archivos_json(tmp_path, capsys):
    codigo = main(["generar-xml", str(EJEMPLOS / "factura.json"), str(EJEMPLOS / "nota-credito.json"),
                   "--salida", str(tmp_path), "--fecha", "2026-10-22"])
    assert codigo == 0
    factura = tmp_path / "20556677884-01-F001-1.xml"
    nota = tmp_path / "20556677884-07-FC01-1.xml"
    assert factura.exists() and nota.exists()
    ValidadorXsdLxml().validar(factura.read_bytes(), TipoComprobante.FACTURA)
    ValidadorXsdLxml().validar(nota.read_bytes(), TipoComprobante.NOTA_CREDITO)
    assert etree.fromstring(factura.read_bytes()).find(".//{http://www.w3.org/2000/09/xmldsig#}DigestValue") is not None
    assert "ACEPTADO" in capsys.readouterr().out


def test_informa_errores_de_contrato_y_de_negocio(tmp_path, capsys):
    malo = tmp_path / "malo.json"
    malo.write_text('{"tipo_comprobante": "01", "serie": "B001", "cliente": {"tipo_documento": "6", '
                    '"numero_documento": "20123456786", "nombre": "X"}, "lineas": [{"descripcion": "a", '
                    '"unidad_medida": "NIU", "cantidad": "1", "valor_unitario": "1"}]}', encoding="utf-8")
    incompleto = tmp_path / "incompleto.json"
    incompleto.write_text('{"tipo_comprobante": "01"}', encoding="utf-8")
    assert main(["generar-xml", str(malo), str(incompleto), "--salida", str(tmp_path / "x"),
                 "--fecha", "2026-10-22"]) == 1
    salida = capsys.readouterr().out
    assert "ERR-SUNAT-SERIE" in salida
    assert "no cumple el contrato" in salida
