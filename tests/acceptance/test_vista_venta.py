"""Vista web "Registrar venta" (Taller 2): formulario → XML UBL 2.1, con memoria y con SQLite."""

from __future__ import annotations

import html
import re
from urllib.parse import urlencode

import pytest
from lxml import etree

FORMULARIO = "application/x-www-form-urlencoded"
MOTO = {
    "tipo": "01", "serie": "FM0T", "cliente_tipo": "6", "cliente_numero": "20123456786",
    "cliente_nombre": "DISTRIBUIDORA DE ABARROTES EL SOL S.A.C.", "cliente_direccion": "JR. COMERCIO 123, LIMA",
    "descripcion": "Motocicleta 150 cc para reparto", "unidad": "NIU", "cantidad": "1",
    "valor_unitario": "4237.29", "afectacion": "10",
}


@pytest.fixture
def enviar(cliente):
    def _enviar(campos: dict | list[tuple[str, str]], **cambios: str):
        datos = list(campos.items()) if isinstance(campos, dict) else list(campos)
        datos = [(k, cambios.pop(k, v)) for k, v in datos] + list(cambios.items())
        return cliente.post("/venta", content=urlencode(datos), headers={"Content-Type": FORMULARIO})

    return _enviar


def xml_de(pagina: str) -> str:
    encontrado = re.search(r'<textarea id="xml"[^>]*>(.*?)</textarea>', pagina, re.S)
    assert encontrado, "la página no muestra el XML"
    return html.unescape(encontrado.group(1))


def aviso_de(pagina: str) -> str:
    return html.unescape(re.search(r'<div class="aviso".*?</div>', pagina, re.S).group(0))


def test_la_raiz_lleva_al_formulario(cliente):
    respuesta = cliente.get("/", follow_redirects=False)
    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == "/venta"


def test_el_formulario_trae_el_caso_de_estudio_y_una_serie_nueva(cliente):
    respuesta = cliente.get("/venta")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "Generar XML" in respuesta.text
    assert "Motocicleta 150 cc para reparto" in respuesta.text and 'value="4237.29"' in respuesta.text
    series = {re.search(r'name="serie" id="serie" value="(F[A-Z0-9]{3})"', cliente.get("/venta").text).group(1)
              for _ in range(5)}
    assert len(series) > 1  # cada visita propone otra serie: evita el error 1033 del OSE-DEMO compartido


def test_la_pagina_declara_cabeceras_de_seguridad(cliente):
    cabeceras = cliente.get("/venta").headers
    assert "default-src 'none'" in cabeceras["content-security-policy"]
    assert "frame-ancestors 'none'" in cabeceras["content-security-policy"]
    assert cabeceras["x-content-type-options"] == "nosniff"


def test_generar_xml_de_la_moto_muestra_importes_matriz_y_xml_sin_firma(enviar):
    respuesta = enviar(MOTO)
    assert respuesta.status_code == 200
    pagina = html.unescape(respuesta.text)
    assert "✓ Válido contra UBL-Invoice-2.1.xsd" in pagina
    assert "CINCO MIL CON 00/100 SOLES" in pagina
    assert "20556677884-01-FM0T-1.xml" in pagina
    assert re.search(r"<td>T62</td>.*?5000\.00", pagina, re.S)  # fila de la matriz con su valor
    xml = xml_de(respuesta.text)
    raiz = etree.fromstring(xml.encode("utf-8"))
    assert etree.QName(raiz).localname == "Invoice"
    assert "UBLExtensions" not in xml and "ds:Signature" not in xml


def test_con_la_casilla_de_firma_el_xml_sale_firmado(enviar):
    respuesta = enviar(MOTO, firmar="si")
    assert respuesta.status_code == 200
    assert "<ds:Signature" in xml_de(respuesta.text)
    assert "Firmado (XMLDSig)" in respuesta.text


def test_varios_productos_y_filas_vacias_ignoradas(enviar):
    campos = [*MOTO.items(), ("descripcion", "Casco certificado"), ("unidad", "NIU"), ("cantidad", "2"),
              ("valor_unitario", "80"), ("afectacion", "20"),
              ("descripcion", ""), ("unidad", "NIU"), ("cantidad", ""), ("valor_unitario", ""), ("afectacion", "10")]
    respuesta = enviar(campos)
    assert respuesta.status_code == 200
    raiz = etree.fromstring(xml_de(respuesta.text).encode("utf-8"))
    ns = {"cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"}
    assert len(raiz.findall("cac:InvoiceLine", ns)) == 2


def test_el_error_de_negocio_vuelve_al_formulario_marcado_en_su_campo(enviar):
    respuesta = enviar(MOTO, tipo="03", serie="BM0T", cliente_tipo="0", cliente_numero="-")
    assert respuesta.status_code == 422
    assert "700" in aviso_de(respuesta.text)
    assert re.search(r'<select name="cliente_tipo" aria-invalid="true"', respuesta.text)
    assert 'value="BM0T"' in respuesta.text  # lo digitado se conserva para corregirlo
    assert 'id="xml"' not in respuesta.text  # nunca se entrega un XML si la venta no cumple


def test_un_numero_mal_escrito_se_rechaza_sin_llegar_al_dominio(enviar):
    respuesta = enviar(MOTO, cantidad="uno")
    assert respuesta.status_code == 400
    assert "La cantidad del producto 1 debe ser un número" in aviso_de(respuesta.text)
    assert re.search(r'name="cantidad" value="uno"[^>]*aria-invalid="true"', respuesta.text)


@pytest.mark.parametrize(("campo", "valor"), [("tipo", "07"), ("cliente_tipo", "X"), ("afectacion", "40"),
                                              ("unidad", "XYZ"), ("valor_unitario", "NaN")])
def test_codigos_fuera_de_las_opciones_del_formulario(enviar, campo, valor):
    assert enviar(MOTO, **{campo: valor}).status_code == 400


def test_sin_productos_no_se_genera(enviar):
    respuesta = enviar(MOTO, descripcion="", cantidad="", valor_unitario="")
    assert respuesta.status_code == 400
    assert "al menos un producto" in aviso_de(respuesta.text)


def test_un_cuerpo_demasiado_grande_se_rechaza(cliente):
    respuesta = cliente.post("/venta", content="descripcion=" + "A" * 40_000, headers={"Content-Type": FORMULARIO})
    assert respuesta.status_code == 413


def test_el_texto_del_usuario_se_escapa_en_la_pagina_y_en_el_xml(enviar):
    respuesta = enviar(MOTO, cliente_nombre="<script>alert(1)</script> & CIA S.A.C.")
    assert respuesta.status_code == 200
    assert "<script>alert(1)</script>" not in respuesta.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; CIA" in xml_de(respuesta.text)


def test_la_vista_no_forma_parte_del_contrato_de_la_api(cliente):
    rutas = cliente.get("/api/v1/openapi.json").json()["paths"]
    assert "/venta" not in rutas and "/" not in rutas
