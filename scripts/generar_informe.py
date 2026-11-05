"""Arma el informe consolidado (PDF y DOCX) desde ``entregable/informe.md``.

Uso:
    scripts/renderizar_diagramas.ps1         # primero: los diagramas .svg y .png
    python scripts/generar_informe.py        # entregable/Informe-ABC-SpecFirst.pdf y .docx

* **PDF:** el Markdown se convierte a HTML con los diagramas SVG (vectoriales) y se imprime con
  Chrome o Edge sin interfaz (``--print-to-pdf``). Otra ruta del navegador: variable ``ABC_CHROME``.
* **DOCX:** el mismo Markdown se escribe con python-docx, con los diagramas en PNG.

El texto vive en el Markdown (versionado y revisable). Si falta un diagrama, el script se
detiene: un informe sin sus figuras no se entrega.
"""

from __future__ import annotations

import argparse
import html
import os
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from docx import Document
from docx.document import Document as DocumentoDocx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph
from markdown_it import MarkdownIt
from markdown_it.token import Token

RAIZ = Path(__file__).resolve().parents[1]
ENTREGABLE = RAIZ / "entregable"
FUENTE = ENTREGABLE / "informe.md"
NOMBRE = "Informe-ABC-SpecFirst"
TEMPORAL = RAIZ / "build" / "informe"

PORTADA = {
    "universidad": "Universidad Nacional Agraria de la Selva",
    "facultad": "Facultad de Ingeniería en Informática y Sistemas",
    "curso": "Arquitectura de Software · Grupo \"A\"",
    "titulo": "ABC Software Corp",
    "subtitulo": "Facturación electrónica UBL 2.1, inventario permanente y libros PLE con Spec-First "
                 "y arquitectura hexagonal",
    "alumno": "Melor Smith Yanac Osorio",
    "entregas": "Fase 1 (Spec-First): 19/10/2026 · Taller 2 (generación del XML): 05/11/2026",
    "repositorio": "https://github.com/Melor-Smith/ARQUITECTURA",
}

NAVEGADORES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)

ESTILO = """
@page { size: A4; margin: 2cm 2cm 2.2cm 2cm; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d1d1f; }
h1 { font-size: 17pt; color: #0b3d6e; border-bottom: 2px solid #0b3d6e; padding-bottom: 4px; margin-top: 0;
     break-before: page; }
h2 { font-size: 13pt; color: #0b3d6e; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 14px; font-size: 9pt; break-inside: avoid; }
th, td { border: 1px solid #b8c4d0; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #e8eef5; }
code { font-family: Consolas, monospace; font-size: 8.8pt; background: #f2f4f7; padding: 0 2px; }
figure { margin: 12px 0 18px; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 21cm; }
figcaption { font-size: 9pt; color: #555; font-style: italic; margin-top: 4px; }
.portada { height: 25cm; display: flex; flex-direction: column; justify-content: space-between; text-align: center; }
.portada .inst { font-size: 13pt; font-weight: 600; color: #0b3d6e; }
.portada .titulo { font-size: 28pt; font-weight: 700; color: #0b3d6e; margin-top: 5cm; }
.portada .sub { font-size: 14pt; margin: 10px 2cm 0; }
.portada .datos { font-size: 11pt; line-height: 1.8; }
"""


def _md() -> MarkdownIt:
    return MarkdownIt("commonmark").enable("table")


def _imagenes(tokens: Sequence[Token]) -> list[str]:
    return [str(hijo.attrGet("src")) for t in tokens if t.type == "inline"
            for hijo in (t.children or []) if hijo.type == "image"]


def verificar_figuras(tokens: Sequence[Token]) -> None:
    faltan = [src for src in _imagenes(tokens)
              for ruta in [(ENTREGABLE / src).resolve()] for formato in (".svg", ".png")
              if not ruta.with_suffix(formato).exists()]
    if faltan:
        raise SystemExit("Faltan diagramas renderizados; ejecute scripts/renderizar_diagramas.ps1:\n  "
                         + "\n  ".join(sorted(set(faltan))))


# --- PDF (HTML + navegador sin interfaz) ---------------------------------------------------
def a_html(texto: str) -> str:
    md = _md()

    def imagen(_renderer: object, tokens: Sequence[Token], i: int, opciones: object, entorno: object) -> str:
        token = tokens[i]
        ruta = (ENTREGABLE / str(token.attrGet("src"))).resolve()
        leyenda = html.escape(token.content)
        return f'<figure><img src="{ruta.as_uri()}" alt="{leyenda}"><figcaption>{leyenda}</figcaption></figure>'

    md.add_render_rule("image", imagen)
    cuerpo = md.render(texto)
    p = {k: html.escape(v) for k, v in PORTADA.items()}
    portada = (f'<section class="portada"><div><div class="inst">{p["universidad"]}</div><div>{p["facultad"]}</div>'
               f'<div>{p["curso"]}</div></div><div><div class="titulo">{p["titulo"]}</div>'
               f'<div class="sub">{p["subtitulo"]}</div></div><div class="datos"><b>Alumno:</b> {p["alumno"]}<br>'
               f'{p["entregas"]}<br>{p["repositorio"]}</div></section>')
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{p["titulo"]}</title>'
            f"<style>{ESTILO}</style></head><body>{portada}{cuerpo}</body></html>")


def navegador() -> str:
    candidatos = [os.environ.get("ABC_CHROME", ""), *NAVEGADORES,
                  *(shutil.which(n) or "" for n in ("chrome", "google-chrome", "chromium", "msedge"))]
    for candidato in candidatos:
        if candidato and Path(candidato).exists():
            return candidato
    raise SystemExit("No se encontró Chrome ni Edge; indique la ruta en ABC_CHROME.")


def generar_pdf(texto: str, destino: Path) -> None:
    TEMPORAL.mkdir(parents=True, exist_ok=True)
    pagina = TEMPORAL / "informe.html"
    pagina.write_text(a_html(texto), encoding="utf-8")
    perfil = TEMPORAL / "perfil-navegador"
    subprocess.run([navegador(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={perfil}", "--allow-file-access-from-files",
                    f"--print-to-pdf={destino}", pagina.as_uri()],
                   check=True, capture_output=True, timeout=180)
    if not destino.exists() or destino.stat().st_size < 10_000:
        raise SystemExit(f"El navegador no produjo {destino.name}")


# --- DOCX ----------------------------------------------------------------------------------
def _escribir_en_linea(parrafo: Paragraph, hijos: Sequence[Token]) -> None:
    negrita = cursiva = False
    for hijo in hijos:
        if hijo.type in ("strong_open", "strong_close"):
            negrita = hijo.type == "strong_open"
        elif hijo.type in ("em_open", "em_close"):
            cursiva = hijo.type == "em_open"
        elif hijo.type in ("text", "code_inline"):
            run = parrafo.add_run(hijo.content)
            run.bold, run.italic = negrita, cursiva
            if hijo.type == "code_inline":
                run.font.name = "Consolas"
                run.font.size = Pt(9)
        elif hijo.type in ("softbreak", "hardbreak"):
            parrafo.add_run(" ")


def _portada(doc: DocumentoDocx) -> None:
    for clave, tamano, negrita, espacio in (("universidad", 14, True, 0), ("facultad", 12, False, 0),
                                            ("curso", 12, False, 0), ("titulo", 28, True, 150),
                                            ("subtitulo", 14, False, 6), ("alumno", 12, True, 150),
                                            ("entregas", 11, False, 6), ("repositorio", 10, False, 0)):
        parrafo = doc.add_paragraph()
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parrafo.paragraph_format.space_before = Pt(espacio)
        texto = f"Alumno: {PORTADA[clave]}" if clave == "alumno" else PORTADA[clave]
        run = parrafo.add_run(texto)
        run.bold, run.font.size = negrita, Pt(tamano)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def generar_docx(texto: str, destino: Path) -> None:
    tokens = _md().parse(texto)
    documento = Document()
    estilo = documento.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(10.5)
    _portada(documento)
    listas: list[str] = []
    primer_titulo = True
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open":
            nivel = int(token.tag[1])
            if nivel == 1 and not primer_titulo:
                documento.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            primer_titulo = False
            documento.add_heading(tokens[i + 1].content, level=nivel)
            i += 3
            continue
        if token.type in ("bullet_list_open", "ordered_list_open"):
            listas.append("List Bullet" if token.type == "bullet_list_open" else "List Number")
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            listas.pop()
        elif token.type == "inline" and tokens[i - 1].type == "paragraph_open":
            hijos = token.children or []
            imagen = next((h for h in hijos if h.type == "image"), None)
            if imagen is not None:
                png = (ENTREGABLE / str(imagen.attrGet("src"))).resolve().with_suffix(".png")
                documento.add_picture(str(png), width=Cm(16))
                documento.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                leyenda = documento.add_paragraph()
                leyenda.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = leyenda.add_run(imagen.content)
                run.italic, run.font.size = True, Pt(9)
            else:
                parrafo = documento.add_paragraph(style=listas[-1] if listas else None)
                _escribir_en_linea(parrafo, hijos)
        elif token.type == "table_open":
            i = _tabla(documento, tokens, i)
        i += 1
    documento.save(str(destino))


def _tabla(doc: DocumentoDocx, tokens: Sequence[Token], inicio: int) -> int:
    filas: list[list[Token]] = []
    i = inicio
    while tokens[i].type != "table_close":
        if tokens[i].type == "tr_open":
            filas.append([])
        elif tokens[i].type == "inline":
            filas[-1].append(tokens[i])
        i += 1
    tabla = doc.add_table(rows=len(filas), cols=max(len(f) for f in filas))
    tabla.style = "Table Grid"
    for r, fila in enumerate(filas):
        for c, celda in enumerate(fila):
            parrafo = tabla.cell(r, c).paragraphs[0]
            _escribir_en_linea(parrafo, celda.children or [])
            for run in parrafo.runs:
                run.font.size = Pt(8.5)
                run.bold = run.bold or r == 0
    return i


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", choices=("pdf", "docx"), help="genera solo uno de los dos formatos")
    parser.add_argument("--salida", type=Path, default=ENTREGABLE, help="carpeta de destino (por defecto entregable/)")
    opciones = parser.parse_args(argumentos)
    texto = FUENTE.read_text(encoding="utf-8")
    verificar_figuras(_md().parse(texto))
    if opciones.solo != "docx":
        generar_pdf(texto, opciones.salida / f"{NOMBRE}.pdf")
        print(f"PDF:  {opciones.salida / f'{NOMBRE}.pdf'}")
    if opciones.solo != "pdf":
        generar_docx(texto, opciones.salida / f"{NOMBRE}.docx")
        print(f"DOCX: {opciones.salida / f'{NOMBRE}.docx'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
