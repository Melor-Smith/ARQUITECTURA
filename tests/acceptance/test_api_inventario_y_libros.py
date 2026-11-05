"""Aceptación HTTP: migración del sistema antiguo, Kardex y libros PLE 14.1 / 12.1."""

from tests.acceptance.test_api_comprobantes import problema
from tests.conftest import ALMACEN, CONSULTA, URL_MIGRACIONES, ejemplo

URL_KARDEX = "/api/v1/inventario/kardex"
URL_141 = "/api/v1/libros-electronicos/registro-ventas"
URL_121 = "/api/v1/libros-electronicos/inventario-unidades-fisicas"


class TestMigracion:
    def test_salida_por_venta_queda_pendiente_de_facturar_sin_numero_sunat(self, migrar):
        r = migrar(ejemplo("ficha-legado-salida.json"))
        assert r.status_code == 201
        cuerpo = r.json()
        assert cuerpo["estado"] == "PENDIENTE_FACTURACION"
        assert "serie_ubl_sugerida" not in cuerpo
        assert cuerpo["movimiento"]["documento"]["tipo"]["codigo"] == "00"  # documento interno, no guía 09
        assert (cuerpo["movimiento"]["documento"]["serie"], cuerpo["movimiento"]["documento"]["numero"]) == (
            "VALE-SALIDA", "0042")
        assert cuerpo["movimiento"]["salida"] == "250"  # 5 sacos x 50 kg
        assert cuerpo["movimiento"]["tipo_operacion"]["codigo"] == "01"
        assert r.headers["location"] == f"{URL_MIGRACIONES}/VALE-SALIDA-0042"

    def test_ingreso_por_compra(self, migrar):
        cuerpo = migrar(ejemplo("ficha-legado-ingreso.json")).json()
        assert (cuerpo["estado"], cuerpo["movimiento"]["tipo_operacion"]["codigo"]) == ("NO_REQUIERE_FACTURA", "02")
        assert cuerpo["movimiento"]["entrada"] == "1000"

    def test_documento_duplicado_409(self, migrar):
        migrar(ejemplo("ficha-legado-salida.json"))
        problema(migrar(ejemplo("ficha-legado-salida.json")), 409, "ERR-LEGADO-DUPLICADO")

    def test_sin_movimiento_es_regla_de_negocio_422(self, migrar):
        problema(migrar(ejemplo("ficha-legado-salida.json") | {"salida": 0}), 422, "ERR-LEGADO-SIN-MOVIMIENTO")

    def test_ingreso_y_salida_a_la_vez(self, migrar):
        problema(migrar(ejemplo("ficha-legado-salida.json") | {"ingreso": 1}), 422, "ERR-LEGADO-AMBIGUA")

    def test_glosa_no_homologada(self, migrar):
        problema(migrar(ejemplo("ficha-legado-salida.json") | {"producto": "Fideos sueltos"}), 422,
                 "ERR-LEGADO-NO-HOMOLOGADO")

    def test_homologacion_explicita(self, migrar):
        r = migrar(ejemplo("ficha-legado-salida.json") | {"producto": "Fideos sueltos", "codigo_producto": "AB-ARR-001",
                                                          "factor_conversion": "1"})
        assert r.status_code == 201

    def test_saldo_insuficiente(self, migrar):
        problema(migrar(ejemplo("ficha-legado-salida.json") | {"salida": 1000}), 422, "ERR-KARDEX-SALDO-INSUFICIENTE")

    def test_tipo_de_operacion_incompatible(self, migrar):
        problema(migrar(ejemplo("ficha-legado-salida.json") | {"tipo_operacion": "02"}), 422,
                 "ERR-KARDEX-TIPO-OPERACION")

    def test_acepta_fechas_escritas_como_en_el_sistema_antiguo(self, migrar):
        r = migrar(ejemplo("ficha-legado-salida.json") | {"fecha": "15/10/2026"})
        assert (r.status_code, r.json()["movimiento"]["fecha"]) == (201, "2026-10-15")

    def test_fecha_imposible_es_regla_de_negocio_422(self, migrar):
        problema(migrar(ejemplo("ficha-legado-salida.json") | {"fecha": "31/09/2026"}), 422, "ERR-LEGADO-FECHA")

    def test_fecha_ausente_es_error_de_contrato_400(self, migrar):
        payload = ejemplo("ficha-legado-salida.json")
        del payload["fecha"]
        problema(migrar(payload), 400)

    def test_factura_fisica_de_compra_se_reconoce_como_tabla_10_tipo_01(self, migrar):
        cuerpo = migrar(ejemplo("ficha-legado-ingreso.json") | {"nro_documento": "FACT 001-4587"}).json()
        assert cuerpo["regla_documento"] == "FACTURA_FISICA"
        documento = cuerpo["movimiento"]["documento"]
        assert (documento["tipo"]["codigo"], documento["serie"], documento["numero"]) == ("01", "0001", "4587")

    def test_salida_con_boleta_del_sistema_antiguo_no_se_vuelve_a_facturar(self, migrar):
        cuerpo = migrar(ejemplo("ficha-legado-salida.json") | {"nro_documento": "B001-0000231"}).json()
        assert (cuerpo["estado"], cuerpo["movimiento"]["documento"]["tipo"]["codigo"]) == (
            "FACTURADA_EN_SISTEMA_ANTIGUO", "03")

    def test_salida_con_guia_de_remision_queda_pendiente_de_facturar(self, migrar):
        cuerpo = migrar(ejemplo("ficha-legado-salida.json") | {"nro_documento": "GUIA 0002-781"}).json()
        assert (cuerpo["estado"], cuerpo["movimiento"]["documento"]["tipo"]["codigo"]) == (
            "PENDIENTE_FACTURACION", "09")

    def test_ficha_sin_documento_se_migra_con_observacion(self, migrar):
        base = ejemplo("ficha-legado-salida.json") | {"nro_documento": "s/n"}
        primera = migrar(base).json()
        assert primera["regla_documento"] == "SIN_DOCUMENTO"
        assert primera["observaciones"] and primera["clave"].startswith("SN-")
        assert migrar(base | {"salida": 2}).status_code == 201  # otra ficha S/N distinta
        problema(migrar(base), 409, "ERR-LEGADO-DUPLICADO")  # la misma ficha S/N repetida


class TestLoteDeMigracion:
    def test_lote_sucio_no_se_detiene_ordena_por_fecha_y_concilia(self, cliente):
        r = cliente.post(f"{URL_MIGRACIONES}/lotes", json=ejemplo("lote-fichas-legado.json"), headers=ALMACEN)
        assert r.status_code == 201
        lote = r.json()
        assert r.headers["location"] == f"{URL_MIGRACIONES}/lotes/{lote['id_lote']}"
        assert lote["resumen"] == {"total": 9, "migradas": 6, "observadas": 2, "duplicadas": 1, "cuadra": True}
        por_indice = {res["indice"]: res for res in lote["resultados"]}
        assert por_indice[7]["codigo"] == "ERR-LEGADO-FECHA"  # 31/09/2026
        assert por_indice[8]["codigo"] == "ERR-LEGADO-NO-HOMOLOGADO"  # Fideos sueltos
        assert por_indice[9]["estado"] == "DUPLICADA"
        assert por_indice[3]["migracion"]["regla_documento"] == "FACTURA_FISICA"
        assert por_indice[4]["migracion"]["estado"] == "FACTURADA_EN_SISTEMA_ANTIGUO"
        assert por_indice[5]["migracion"]["observaciones"]  # s/n
        # El Kardex exige orden cronológico: el lote se aplicó por fecha aunque el archivo venía desordenado.
        azucar = next(c for c in lote["conciliacion"] if c["codigo_producto"] == "AB-AZU-001")
        assert (azucar["saldo_inicial"], azucar["salidas"], azucar["saldo_final"]) == ("1000", "300", "700")

    def test_reprocesar_el_mismo_lote_es_seguro(self, cliente):
        cliente.post(f"{URL_MIGRACIONES}/lotes", json=ejemplo("lote-fichas-legado.json"), headers=ALMACEN)
        segundo = cliente.post(f"{URL_MIGRACIONES}/lotes", json=ejemplo("lote-fichas-legado.json"),
                               headers=ALMACEN).json()
        assert segundo["resumen"]["migradas"] == 0
        assert segundo["resumen"]["duplicadas"] == 7

    def test_consultar_lote(self, cliente):
        id_lote = cliente.post(f"{URL_MIGRACIONES}/lotes", json=ejemplo("lote-fichas-legado.json"),
                               headers=ALMACEN).json()["id_lote"]
        assert cliente.get(f"{URL_MIGRACIONES}/lotes/{id_lote}", headers=CONSULTA).json()["id_lote"] == id_lote
        problema(cliente.get(f"{URL_MIGRACIONES}/lotes/LOTE-999999", headers=CONSULTA), 404)


class TestFacturacionDeValesLegado:
    def test_factura_del_vale_lo_marca_facturado_y_no_duplica_la_salida(self, migrar, emitir, cliente):
        migrar(ejemplo("ficha-legado-salida.json"))
        r = emitir(ejemplo("factura-de-vale-legado.json"))
        assert (r.status_code, r.json()["documentos_legado"]) == (201, ["VALE-SALIDA-0042"])
        migracion = cliente.get(f"{URL_MIGRACIONES}/VALE-SALIDA-0042", headers=CONSULTA).json()
        assert (migracion["estado"], migracion["comprobante"]) == ("FACTURADA", "01/F001-1")
        kardex = cliente.get(f"{URL_KARDEX}/AB-AZU-001", headers=CONSULTA).json()
        assert kardex["saldo_final"] == "750"  # 1000 - 250 una sola vez

    def test_el_xml_referencia_el_vale_como_documento_relacionado_99(self, migrar, emitir, cliente):
        migrar(ejemplo("ficha-legado-salida.json"))
        cuerpo = emitir(ejemplo("factura-de-vale-legado.json")).json()
        xml = cliente.get(cuerpo["enlaces"]["xml"], headers=CONSULTA).content
        assert b"<cac:AdditionalDocumentReference><cbc:ID>VALE-SALIDA-0042</cbc:ID>" in xml
        assert b"DespatchDocumentReference" not in xml

    def test_un_vale_no_se_factura_dos_veces(self, migrar, emitir):
        migrar(ejemplo("ficha-legado-salida.json"))
        emitir(ejemplo("factura-de-vale-legado.json"))
        problema(emitir(ejemplo("factura-de-vale-legado.json")), 409, "ERR-LEGADO-YA-FACTURADO")

    def test_vale_no_migrado(self, emitir):
        problema(emitir(ejemplo("factura-de-vale-legado.json")), 422, "ERR-LEGADO-NO-MIGRADO")

    def test_vale_de_otro_producto(self, migrar, emitir):
        migrar(ejemplo("ficha-legado-salida.json"))
        problema(emitir(ejemplo("factura.json") | {"documentos_legado": ["VALE-SALIDA-0042"],
                                                   "lineas": ejemplo("factura.json")["lineas"][:1]}),
                 422, "ERR-LEGADO-NO-CORRESPONDE")


class TestKardex:
    def test_kardex_con_saldo_final_y_equivalencia_de_unidades(self, cliente):
        cuerpo = cliente.get(f"{URL_KARDEX}/AB-ARR-001", headers=CONSULTA).json()
        assert cuerpo["saldo_final"] == "2000"
        assert cuerpo["producto"]["unidad_medida"]["codigo"] == "KGM"
        assert cuerpo["producto"]["unidad_medida_ple"]["codigo"] == "01"
        assert cuerpo["producto"]["tipo_existencia"]["codigo"] == "01"

    def test_producto_inexistente(self, cliente):
        problema(cliente.get(f"{URL_KARDEX}/NO-EXISTE", headers=CONSULTA), 404)


class TestRegistroVentas141:
    def test_txt_del_ple(self, emitir, cliente):
        emitir(ejemplo("factura.json"))
        emitir(ejemplo("nota-credito.json"))
        r = cliente.get(f"{URL_141}/202610", headers=CONSULTA)
        assert r.headers["content-type"].startswith("text/plain")
        assert 'filename="LE2055667788420261000140100001111.txt"' in r.headers["content-disposition"]
        factura, nota = (ln.split("|") for ln in r.text.strip().split("\r\n"))
        assert len(factura) == 36  # 35 campos + separador final
        assert factura[:8] == ["20261000", "V202610000001", "M1", "22/10/2026", "", "01", "F001", "1"]
        assert (factura[13], factura[15], factura[24]) == ("305.00", "54.90", "359.90")
        assert (nota[5], nota[24], nota[28:31]) == ("07", "-49.56", ["01", "F001", "1"])

    def test_comprobantes_rechazados_no_se_anotan(self, emitir, cliente, contenedor):
        from src.adapters.outbound.ose.simulada import ModoOse

        contenedor.ose.modo = ModoOse.RECHAZO
        emitir(ejemplo("factura.json"))
        r = cliente.get(f"{URL_141}/202610", headers=CONSULTA)
        assert r.text == ""
        # posición 30 = 1 (empresa operativa), posición 31 = 0 (libro sin información)
        assert "140100001011.txt" in r.headers["content-disposition"]

    def test_vista_json(self, emitir, cliente):
        emitir(ejemplo("boleta.json"))
        cuerpo = cliente.get(f"{URL_141}/202610?formato=json", headers=CONSULTA).json()
        assert (cuerpo["formato"], cuerpo["filas"][0]["tipo_comprobante"]) == ("14.1", "03")

    def test_periodo_invalido(self, cliente):
        problema(cliente.get(f"{URL_141}/202613", headers=CONSULTA), 400)


class TestInventario121:
    def test_txt_con_tabla_6_tabla_10_y_tabla_12(self, migrar, emitir, cliente):
        migrar(ejemplo("ficha-legado-salida.json"))
        emitir(ejemplo("factura-de-vale-legado.json"))
        r = cliente.get(f"{URL_121}/202610", headers=CONSULTA)
        filas = [ln.split("|") for ln in r.text.strip().split("\r\n")]
        azucar = [f for f in filas if f[6] == "AB-AZU-001"]
        saldo_inicial, vale = azucar
        assert len(vale) == 20  # 19 campos del Anexo 2 (PLE 5.0) + separador final
        assert (saldo_inicial[13], saldo_inicial[16]) == ("16", "1000.00")
        assert vale[7:9] == ["", ""]  # 8 y 9: catálogo internacional (UNSPSC/GTIN), opcional
        assert vale[10:14] == ["00", "VALE-SALIDA", "0042", "01"]
        assert (vale[15], vale[16], vale[17]) == ("01", "0.00", "-250.00")  # tabla 6: 01 = kg; salida negativa
