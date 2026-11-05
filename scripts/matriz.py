"""Genera la matriz de trazabilidad desde ``specs/traceability/matriz.yaml``.

Para cada fila con XPath, la cardinalidad NO se escribe a mano: se calcula recorriendo los
XSD oficiales de OASIS UBL 2.1 (``specs/contracts/ubl-2.1/xsd``). Si SUNAT exige un dato que
el XSD deja opcional en algún punto de la ruta, la fila se marca como "brecha de perfil": el
XSD por sí solo no basta y la regla vive en el dominio.

Uso:  python scripts/matriz.py        (regenera el bloque de la matriz en Markdown y el CSV)
La prueba tests/integration/test_matriz.py falla si los archivos quedan desactualizados.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from lxml import etree

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "specs" / "traceability" / "matriz.yaml"
DESTINO_MD = RAIZ / "specs" / "traceability" / "matriz-trazabilidad.md"
DESTINO_CSV = RAIZ / "specs" / "traceability" / "matriz.csv"
DIRECTORIO_XSD = RAIZ / "specs" / "contracts" / "ubl-2.1" / "xsd"
INICIO, FIN = "<!-- matriz:inicio (generado por scripts/matriz.py) -->", "<!-- matriz:fin -->"

XS = "http://www.w3.org/2001/XMLSchema"
PREFIJOS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}
RAICES = {
    "Invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "CreditNote": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    "DebitNote": "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2",
}

Nombre = tuple[str, str]  # (namespace, nombre local)


@dataclass(frozen=True)
class Cardinalidad:
    texto: str  # p. ej. "0..1", "1..n", "atributo opcional"
    obligatorio_en_xsd: bool  # True si cada paso de la ruta tiene minOccurs >= 1
    ruta: str  # cardinalidad de cada paso, para auditar el cálculo


class EsquemaUBL:
    """Índice mínimo de los XSD: elementos globales → tipo, y tipo complejo → hijos con cardinalidad."""

    def __init__(self, directorio: Path = DIRECTORIO_XSD) -> None:
        self.elementos: dict[Nombre, Nombre | None] = {}
        self.hijos: dict[Nombre, list[tuple[Nombre, int, str]]] = {}
        self.con_any: set[Nombre] = set()
        self.atributos: dict[Nombre, dict[str, str]] = {}  # tipo → {atributo: use}
        self.base: dict[Nombre, Nombre] = {}  # tipo → tipo base (extension/restriction)
        for archivo in sorted(directorio.rglob("*.xsd")):
            raiz = etree.parse(str(archivo)).getroot()
            tns = raiz.get("targetNamespace", "")
            for el in raiz.findall(f"{{{XS}}}element"):
                tipo = el.get("type")
                self.elementos[(tns, el.get("name"))] = self._resolver(tipo, el) if tipo else None
            for tipo in raiz.findall(f"{{{XS}}}complexType"):
                nombre = (tns, tipo.get("name"))
                hijos = []
                for e in tipo.iter(f"{{{XS}}}element"):
                    destino = self._resolver(e.get("ref"), e) if e.get("ref") else (tns, e.get("name"))
                    if not e.get("ref") and e.get("type"):
                        self.elementos.setdefault(destino, self._resolver(e.get("type"), e))
                    hijos.append((destino, int(e.get("minOccurs", "1")), e.get("maxOccurs", "1")))
                if tipo.find(f".//{{{XS}}}any") is not None:
                    self.con_any.add(nombre)
                self.hijos[nombre] = hijos
                self.atributos[nombre] = {a.get("name"): a.get("use", "optional")
                                          for a in tipo.iter(f"{{{XS}}}attribute") if a.get("name")}
                derivacion = tipo.find(f".//{{{XS}}}extension")
                if derivacion is None:
                    derivacion = tipo.find(f".//{{{XS}}}restriction")
                if derivacion is not None and derivacion.get("base"):
                    self.base[nombre] = self._resolver(derivacion.get("base"), derivacion)

    def _uso_atributo(self, tipo: Nombre | None, atributo: str) -> str:
        """Busca el atributo en el tipo y, si no está, en sus tipos base (el más derivado manda)."""
        while tipo is not None:
            if atributo in self.atributos.get(tipo, {}):
                return self.atributos[tipo][atributo]
            tipo = self.base.get(tipo)
        raise ValueError(f"El atributo '{atributo}' no existe en el tipo ni en sus bases")

    @staticmethod
    def _resolver(qname: str, nodo: etree._Element) -> Nombre:
        prefijo, _, local = qname.rpartition(":")
        return nodo.nsmap.get(prefijo or None, ""), local

    def cardinalidad(self, xpath: str) -> Cardinalidad:
        sin_predicados = re.sub(r"\[[^\]]*\]", "", xpath)
        pasos = [p for p in sin_predicados.split("/") if p]
        raiz = pasos[0]
        tipo = self.elementos[(RAICES[raiz], raiz)]
        obligatorio, ruta, texto = True, [raiz], "1..1"
        for paso in pasos[1:]:
            if paso.startswith("@"):
                requerido = self._uso_atributo(tipo, paso[1:]) == "required"
                texto = "atributo obligatorio" if requerido else "atributo opcional"
                obligatorio = obligatorio and requerido
                ruta.append(f"{paso} {'1' if requerido else '0..1'}")
                break
            if tipo is None:
                raise ValueError(f"'{paso}': el elemento anterior no tiene un tipo complejo en el XSD (ruta {xpath})")
            prefijo, _, local = paso.partition(":")
            nombre = (PREFIJOS[prefijo], local)
            hijo = next((h for h in self.hijos.get(tipo, []) if h[0] == nombre), None)
            if hijo is None and tipo in self.con_any:
                minimo, maximo = 1, "1"  # contenido abierto (xsd:any), p. ej. la firma en ExtensionContent
                texto_paso = f"{local} (xsd:any)"
            elif hijo is None:
                raise ValueError(f"'{paso}' no es hijo de {tipo[1]} en el XSD (ruta {xpath})")
            else:
                _, minimo, maximo = hijo
                texto_paso = f"{local} {minimo}..{'n' if maximo == 'unbounded' else maximo}"
            texto = f"{minimo}..{'n' if maximo == 'unbounded' else maximo}"
            obligatorio = obligatorio and minimo >= 1
            ruta.append(texto_paso)
            tipo = self.elementos.get(nombre)
        return Cardinalidad(texto, obligatorio, " › ".join(ruta))


COLUMNAS = ["ID", "Dato", "Norma / catálogo", "SUNAT", "XPath UBL 2.1", "Card. XSD", "Perfil SUNAT",
            "Contrato (JSON)", "Sistema antiguo", "14.1", "12.1", "Error", "Prueba"]


def filas(esquema: EsquemaUBL | None = None) -> list[tuple[str, list[str]]]:
    """Devuelve [(título de sección, celdas), ...] con la cardinalidad calculada."""
    esquema = esquema or EsquemaUBL()
    fuente = yaml.safe_load(FUENTE.read_text(encoding="utf-8"))
    resultado = []
    for seccion in fuente["secciones"]:
        for f in seccion["filas"]:
            if f.get("xpath"):
                card = esquema.cardinalidad(f["xpath"])
                brecha = "⚠ SUNAT exige; XSD opcional" if f["sunat"] == "O" and not card.obligatorio_en_xsd else ""
                xsd = card.texto
            else:
                xsd, brecha = "—", ""
            resultado.append((seccion["titulo"], [
                f["id"], f["dato"], f.get("norma", "—"), f.get("sunat", "—"), f.get("xpath", "—"), xsd, brecha,
                f.get("contrato", "—"), f.get("legado", "—"), str(f.get("ple_141", "—")), str(f.get("ple_121", "—")),
                f.get("error", "—"), f.get("prueba", "—"),
            ]))
    return resultado


def _celda(valor: str, columna: str) -> str:
    if valor in ("—", ""):
        return valor
    if columna in ("XPath UBL 2.1", "Contrato (JSON)", "Error", "Prueba", "Sistema antiguo"):
        return f"`{valor}`"
    return valor


def markdown(datos: list[tuple[str, list[str]]]) -> str:
    salida, seccion_actual = [], None
    for titulo, celdas in datos:
        if titulo != seccion_actual:
            seccion_actual = titulo
            salida += ["", f"### {titulo}", "", "| " + " | ".join(COLUMNAS) + " |",
                       "|" + "---|" * len(COLUMNAS)]
        valores = (_celda(v, c).replace("|", "\\|") for v, c in zip(celdas, COLUMNAS, strict=True))
        salida.append("| " + " | ".join(valores) + " |")
    brechas = sum(1 for _, c in datos if c[6])
    con_xpath = sum(1 for _, c in datos if c[4] != "—")
    salida += ["", f"*{len(datos)} filas; {con_xpath} con XPath verificado contra XML generados; {brechas} brechas "
                   "de perfil (dato que SUNAT exige y el XSD de OASIS deja opcional).*"]
    return "\n".join(salida)


def csv_texto(datos: list[tuple[str, list[str]]]) -> str:
    buffer = io.StringIO()
    escritor = csv.writer(buffer, lineterminator="\n")
    escritor.writerow(["Sección", *COLUMNAS])
    for titulo, celdas in datos:
        escritor.writerow([titulo, *celdas])
    return buffer.getvalue()


def documento_markdown(datos: list[tuple[str, list[str]]]) -> str:
    actual = DESTINO_MD.read_text(encoding="utf-8")
    antes, _, resto = actual.partition(INICIO)
    _, _, despues = resto.partition(FIN)
    return f"{antes}{INICIO}\n{markdown(datos)}\n\n{FIN}{despues}"


def main() -> None:
    datos = filas()
    DESTINO_MD.write_text(documento_markdown(datos), encoding="utf-8")
    DESTINO_CSV.write_text(csv_texto(datos), encoding="utf-8-sig")
    print(f"Matriz regenerada: {len(datos)} filas -> {DESTINO_MD.relative_to(RAIZ)} y {DESTINO_CSV.relative_to(RAIZ)}")


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    main()
