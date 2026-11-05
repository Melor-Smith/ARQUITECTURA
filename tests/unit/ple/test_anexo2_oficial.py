"""La estructura del dominio se contrasta con el Excel oficial de SUNAT, no con una transcripción.

Fuente: ``specs/ple/anexo2/estructuras-ple-5.0.xls`` (Anexo 2 de la RS 286-2009/SUNAT,
"Estructuras e información de los libros y/o registros electrónicos", PLE 5.0). Si SUNAT
publica otra versión, basta reemplazar el archivo: estas pruebas dirán qué campos cambiaron.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from src.domain.libros import FilaInventario121, FilaRegistroVentas141, LibroElectronico, Periodo
from src.domain.ple_estructura import ESTRUCTURA_121, ESTRUCTURA_141, Campo, TipoDato
from src.domain.valores import Ruc

xlrd = pytest.importorskip("xlrd")

ANEXO2 = Path(__file__).resolve().parents[3] / "specs" / "ple" / "anexo2" / "estructuras-ple-5.0.xls"

_FORMATO = {
    "Numérico": {TipoDato.NUMERICO, TipoDato.IMPORTE, TipoDato.TIPO_CAMBIO},
    "Texto": {TipoDato.TEXTO},
    "Alfanumérico": {TipoDato.ALFANUMERICO},
    "DD/MM/AAAA": {TipoDato.FECHA},
}


@dataclasses.dataclass(frozen=True)
class CampoOficial:
    numero: int
    longitud: str
    obligatorio: bool
    formato: str


def _leer(hoja: str, titulo: str) -> tuple[list[CampoOficial], str]:
    """Filas de la estructura cuyo título empieza con ``titulo``, hasta los campos libres."""
    libro = xlrd.open_workbook(str(ANEXO2))
    s = libro.sheet_by_name(hoja)
    filas = [[" ".join(str(c.value).split()) for c in s.row(r)] for r in range(s.nrows)]
    inicio = next(i for i, f in enumerate(filas) if f[0].startswith(titulo)) + 2  # salta la cabecera
    campos: list[CampoOficial] = []
    for f in filas[inicio:]:
        if " al " in f[0]:  # "36 al 70": campos de libre utilización
            return campos, f[0]
        campos.append(CampoOficial(int(float(f[0])), f[1], f[2] == "Si", f[5]))
    raise AssertionError("no se encontró el fin de la estructura")


def _longitud(texto: str) -> tuple[TipoDato | None, int]:
    t = texto.replace("\n", " ")
    if "12 enteros" in t:
        return TipoDato.IMPORTE, 12
    if "1 entero y 3 decimales" in t:
        return TipoDato.TIPO_CAMBIO, 1
    return None, int(float(re.findall(r"\d+(?:\.\d+)?", t)[-1]))


ESTRUCTURAS = [
    pytest.param("14 Registro de Ventas", "14.1 ", ESTRUCTURA_141, FilaRegistroVentas141, id="14.1"),
    pytest.param("12 Reg. Inv. Perm. Und. Fisicas", "12.1 ", ESTRUCTURA_121, FilaInventario121, id="12.1"),
]


@pytest.mark.parametrize(("hoja", "titulo", "estructura", "fila"), ESTRUCTURAS)
class TestEstructuraContraElAnexo2:
    def test_mismo_numero_de_campos_y_en_el_mismo_orden(self, hoja, titulo, estructura, fila):
        oficiales, libres = _leer(hoja, titulo)
        assert [c.numero for c in estructura] == [o.numero for o in oficiales] == list(range(1, len(oficiales) + 1))
        # los campos de libre utilización empiezan justo después del último obligatorio por estructura
        assert libres.startswith(f"{len(oficiales) + 1} al")

    def test_tipo_longitud_y_obligatoriedad_de_cada_campo(self, hoja, titulo, estructura, fila):
        oficiales, _ = _leer(hoja, titulo)
        diferencias = []
        for nuestro, oficial in zip(estructura, oficiales, strict=True):
            tipo_por_longitud, longitud = _longitud(oficial.longitud)
            esperado = (oficial.obligatorio, longitud, True)
            obtenido = (nuestro.obligatorio, nuestro.longitud_max,
                        nuestro.tipo in _FORMATO[oficial.formato]
                        and (tipo_por_longitud is None or nuestro.tipo is tipo_por_longitud))
            if esperado != obtenido:
                diferencias.append((nuestro.numero, nuestro.nombre, esperado, obtenido))
        assert diferencias == []

    def test_cada_campo_sale_de_un_atributo_de_la_fila_del_dominio(self, hoja, titulo, estructura, fila):
        solo_vista = {"saldo_final"}
        atributos = [f.name for f in dataclasses.fields(fila) if f.name not in solo_vista]
        assert [c.atributo for c in estructura] == atributos


def _plantilla_nombre(codigo: str) -> str:
    libro = xlrd.open_workbook(str(ANEXO2))
    s = libro.sheet_by_name("Reglas de nombres de libros")
    for r in range(s.nrows):
        fila = [str(c.value).strip() for c in s.row(r)]
        if codigo in fila[3]:
            return fila[4]
    raise AssertionError(codigo)


@pytest.mark.parametrize("codigo", ["140100", "120100"])
@pytest.mark.parametrize("con_filas", [True, False])
def test_nombre_del_archivo_sigue_la_plantilla_oficial(codigo, con_filas):
    plantilla = _plantilla_nombre(codigo)  # p. ej. LERRRRRRRRRRRAAAAMM0014010000OIM1.TXT
    patron = (plantilla.replace("RRRRRRRRRRR", r"\d{11}").replace("AAAA", r"\d{4}").replace("MM", r"(0[1-9]|1[0-2])", 1)
              .replace("OIM1", "(?P<O>[012])(?P<I>[01])(?P<M>[12])1").replace(".TXT", r"\.TXT"))
    libro = LibroElectronico(codigo, Ruc("20556677884"), Periodo(2026, 10), ("fila",) if con_filas else ())
    coincidencia = re.fullmatch(patron, libro.nombre_archivo, flags=re.IGNORECASE)
    assert coincidencia, (libro.nombre_archivo, plantilla)
    assert coincidencia["O"] == "1"  # empresa operativa (0 sería baja del RUC)
    assert coincidencia["I"] == ("1" if con_filas else "0")
    assert coincidencia["M"] == "1"  # soles


def test_las_dos_estructuras_usan_campos_bien_formados():
    for campo in (*ESTRUCTURA_141, *ESTRUCTURA_121):
        assert isinstance(campo, Campo) and campo.longitud_min <= max(campo.longitud_max, 1)
