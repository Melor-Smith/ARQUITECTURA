"""Vista (la V de MVC) del formulario "Registrar venta" y de su resultado: el XML UBL 2.1.

HTML hecho en el servidor, sin librerías externas ni lógica de negocio. El JavaScript solo agrega
o quita filas, cambia la letra de la serie y descarga o copia el XML. Los impuestos y los totales
que se muestran salen del dominio, nunca del navegador.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from src.adapters.inbound.http.formulario_venta import (
    AFECTACIONES,
    DOCUMENTOS,
    TIPOS,
    UNIDADES,
    FormularioVenta,
    LineaFormulario,
)
from src.adapters.inbound.http.vistas.matriz_ubl import FilaMatriz
from src.application.casos_uso.venta_xml import XmlDeVenta

#: El XML generado puede validarse en el OSE-DEMO de Nubefact (docs/evidencia-nubefact).
URL_NUBEFACT = "https://probar-xml.nubefact.com/"

CABECERAS_SEGURIDAD = {
    "Content-Security-Policy": ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                                "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


@dataclass(frozen=True, slots=True)
class Aviso:
    """Error que se muestra en la página, marcado en el campo que lo causó."""

    mensaje: str
    codigo: str
    campo: str | None = None
    detalles: tuple[str, ...] = ()


def _e(valor: object) -> str:
    return escape(str(valor), quote=True)


def _opciones(opciones, actual: str, *, etiqueta=lambda o: f"{o.value} · {o.descripcion}") -> str:
    return "".join(
        f'<option value="{_e(o.value)}"{" selected" if o.value == actual else ""}>{_e(etiqueta(o))}</option>'
        for o in opciones
    )


def _error(aviso: Aviso | None, *campos: str) -> str:
    """Atributos que marcan un campo con error (``aria-invalid``) si el aviso lo señala."""
    if aviso is None or aviso.campo is None or aviso.campo not in campos:
        return ""
    return ' aria-invalid="true"'


def _fila(i: int, ln: LineaFormulario, aviso: Aviso | None) -> str:
    c = f"lineas[{i}]"
    return f"""
      <tr>
        <td><input name="descripcion" value="{_e(ln.descripcion)}" maxlength="500" required
                   aria-label="Descripción"{_error(aviso, f"{c}.descripcion", c)}></td>
        <td><select name="unidad" aria-label="Unidad"{_error(aviso, f"{c}.unidad_medida")}>
              {_opciones(UNIDADES, ln.unidad, etiqueta=lambda o: o.value)}</select></td>
        <td><input name="cantidad" value="{_e(ln.cantidad)}" inputmode="decimal" required class="num"
                   aria-label="Cantidad"{_error(aviso, f"{c}.cantidad")}></td>
        <td><input name="valor_unitario" value="{_e(ln.valor_unitario)}" inputmode="decimal" required class="num"
                   aria-label="Valor unitario sin IGV"{_error(aviso, f"{c}.valor_unitario")}></td>
        <td><select name="afectacion" aria-label="Afectación del IGV"{_error(aviso, f"{c}.afectacion_igv")}>
              {_opciones(AFECTACIONES, ln.afectacion)}</select></td>
        <td><button type="button" class="quitar" title="Quitar producto" aria-label="Quitar producto">×</button></td>
      </tr>"""


def _formulario(f: FormularioVenta, aviso: Aviso | None) -> str:
    lineas = f.lineas or [LineaFormulario()]
    filas = "".join(_fila(i, ln, aviso) for i, ln in enumerate(lineas))
    return f"""
  <form method="post" action="/venta" class="tarjeta" id="venta" novalidate>
    <h2><span class="paso">1</span> Registrar venta</h2>

    <fieldset>
      <legend>Comprobante</legend>
      <div class="grupo">
        <label>Tipo (Cat. 01)
          <select name="tipo" id="tipo"{_error(aviso, "tipo_comprobante")}>{_opciones(TIPOS, f.tipo)}</select>
        </label>
        <label>Serie
          <input name="serie" id="serie" value="{_e(f.serie)}" maxlength="4" pattern="[FB][A-Z0-9]{{3}}"
                 autocomplete="off" required{_error(aviso, "serie")}>
        </label>
        <label>Correlativo
          <input value="automático" disabled title="Lo asigna el sistema al generar, después de validar">
        </label>
      </div>
      <p class="ayuda">Factura → serie F y cliente con RUC. Boleta → serie B. Cada vez que abres el formulario
        se propone una serie nueva, porque el OSE-DEMO es compartido y un número repetido da el error 1033.</p>
    </fieldset>

    <fieldset>
      <legend>Cliente</legend>
      <div class="grupo">
        <label>Documento (Cat. 06)
          <select name="cliente_tipo"{_error(aviso, "cliente.tipo_documento")}>
            {_opciones(DOCUMENTOS, f.cliente_tipo)}</select>
        </label>
        <label>Número
          <input name="cliente_numero" value="{_e(f.cliente_numero)}" maxlength="15" autocomplete="off"
                 required{_error(aviso, "cliente.numero_documento", "ruc")}>
        </label>
      </div>
      <label>Nombre o razón social
        <input name="cliente_nombre" value="{_e(f.cliente_nombre)}" maxlength="200"
               required{_error(aviso, "cliente.nombre")}>
      </label>
      <label>Dirección <small>(opcional)</small>
        <input name="cliente_direccion" value="{_e(f.cliente_direccion)}" maxlength="250"
               {_error(aviso, "cliente.direccion")}>
      </label>
    </fieldset>

    <fieldset>
      <legend>Productos</legend>
      <div class="tabla-desplazable">
        <table class="productos">
          <thead><tr><th>Descripción</th><th>Unidad</th><th>Cantidad</th><th>Valor unit. sin IGV</th>
            <th>Afectación (Cat. 07)</th><th></th></tr></thead>
          <tbody id="filas">{filas}</tbody>
        </table>
      </div>
      <button type="button" id="agregar" class="secundario">+ Agregar producto</button>
      <p class="ayuda">El <b>valor unitario</b> va sin IGV, como lo pide SUNAT. El IGV, los totales y el importe
        en letras los calcula el dominio. El producto es libre: no tiene que existir en el inventario.</p>
    </fieldset>

    <label class="casilla">
      <input type="checkbox" name="firmar" value="si"{" checked" if f.firmar else ""}>
      Incluir firma digital (XMLDSig, certificado de prueba)
    </label>
    <p class="ayuda">Desmarcado, el XML sale <b>sin firma</b> para probarlo en Nubefact, que lo firma con su
      certificado de prueba.</p>

    <button type="submit" class="principal">Generar XML</button>
  </form>
  <template id="plantilla-fila">{_fila(0, LineaFormulario(), None)}</template>"""


def _importe(etiqueta: str, valor, *, fuerte: bool = False) -> str:
    clase = ' class="total"' if fuerte else ""
    return f"<tr{clase}><th>{_e(etiqueta)}</th><td class=\"num\">S/ {_e(valor)}</td></tr>"


def _fila_matriz(f: FilaMatriz) -> str:
    obligatorio = ' <span class="o" title="Obligatorio para SUNAT">O</span>' if f.obligatorio else ""
    etiqueta = f.xpath.split("/", 2)[-1]  # sin la raíz: /Invoice/cbc:ID -> cbc:ID
    return (f"<tr><td>{_e(f.id)}</td><td>{_e(f.dato)}{obligatorio}</td><td>{_e(f.norma)}</td>"
            f'<td><code title="{_e(f.xpath)}">{_e(etiqueta)}</code></td><td class="valor">{_e(f.valor)}</td></tr>')


def _resultado(r: XmlDeVenta, filas: list[FilaMatriz]) -> str:
    c, t = r.comprobante, r.comprobante.totales
    importes = [_importe("Op. gravadas", t.gravadas)] if t.gravadas else []
    importes += [_importe("Op. exoneradas", t.exoneradas)] if t.exoneradas else []
    importes += [_importe("Op. inafectas", t.inafectas)] if t.inafectas else []
    importes += [_importe("IGV 18 %", t.igv), _importe("Importe total", t.importe_total, fuerte=True)]
    lineas = "".join(
        f"<tr><td>{ln.numero}</td><td>{_e(ln.descripcion)}</td><td class=\"num\">{_e(ln.cantidad)} "
        f"{_e(ln.unidad.value)}</td><td class=\"num\">{_e(ln.valor_venta)}</td><td class=\"num\">{_e(ln.monto_igv)}"
        f"</td><td class=\"num\">{_e(ln.precio_unitario)}</td></tr>"
        for ln in c.lineas
    )
    matriz = "".join(_fila_matriz(f) for f in filas) or (
        '<tr><td colspan="5">La matriz de trazabilidad no está disponible en esta instalación.</td></tr>')
    firma = ("Firmado (XMLDSig)" if r.firmado else "Sin firma (ext:UBLExtensions omitido)")
    xml = r.xml.decode("utf-8")
    return f"""
  <section class="tarjeta" aria-labelledby="t-resultado">
    <h2 id="t-resultado"><span class="paso">2</span> XML generado</h2>
    <ul class="estado">
      <li class="ok">✓ Válido contra UBL-Invoice-2.1.xsd</li>
      <li>{_e(c.tipo.descripcion)} {_e(c.serie_numero)}</li>
      <li>{_e(firma)}</li>
      <li>Emitido {_e(c.fecha_emision.isoformat())} {_e(c.hora_emision.isoformat())}</li>
    </ul>

    <div class="dos">
      <table class="importes">{"".join(importes)}</table>
      <p class="letras">{_e(c.monto_en_letras)}<br><small>Leyenda 1000 (Cat. 52)</small></p>
    </div>

    <h3>Productos calculados por el dominio</h3>
    <div class="tabla-desplazable">
      <table class="detalle">
        <thead><tr><th>#</th><th>Descripción</th><th>Cantidad</th><th>Valor venta</th><th>IGV</th>
          <th>Precio unit. con IGV</th></tr></thead>
        <tbody>{lineas}</tbody>
      </table>
    </div>

    <details open>
      <summary>Matriz: qué dato SUNAT quedó en qué etiqueta UBL ({len(filas)} datos)</summary>
      <p class="ayuda">Cada fila sale de la matriz de trazabilidad del proyecto
        (<code>specs/traceability/matriz.csv</code>). Su XPath se evaluó sobre este XML y la última columna
        muestra el valor encontrado.</p>
      <div class="tabla-desplazable">
        <table class="matriz">
          <thead><tr><th>ID</th><th>Dato</th><th>Norma / catálogo</th><th>Etiqueta UBL 2.1</th><th>Valor</th></tr>
          </thead>
          <tbody>{matriz}</tbody>
        </table>
      </div>
    </details>

    <h3>Archivo <code>{_e(r.nombre_archivo)}</code></h3>
    <div class="acciones">
      <button type="button" class="principal" id="descargar" data-nombre="{_e(r.nombre_archivo)}">Descargar XML</button>
      <button type="button" class="secundario" id="copiar">Copiar XML</button>
      <a href="{URL_NUBEFACT}" target="_blank" rel="noopener noreferrer">Probar en Nubefact (OSE-DEMO) ↗</a>
    </div>
    <p class="ayuda">En Nubefact: pega el XML, deja el destino <b>OSE</b>, marca <b>Firmar</b> y pulsa
      <b>Enviar</b>. La respuesta esperada es un CDR con código 0: «ha sido ACEPTADA».</p>
    <textarea id="xml" readonly spellcheck="false" aria-label="XML UBL 2.1 generado">{_e(xml)}</textarea>
  </section>"""


def _vacio() -> str:
    return """
  <section class="tarjeta vacio" aria-labelledby="t-resultado">
    <h2 id="t-resultado"><span class="paso">2</span> XML generado</h2>
    <p>Registra la venta y pulsa <b>Generar XML</b>. Aquí verás:</p>
    <ol>
      <li>los importes que calculó el dominio (valor de venta, IGV 18 %, total y monto en letras);</li>
      <li>la matriz con cada dato SUNAT y la etiqueta UBL 2.1 donde quedó;</li>
      <li>el XML validado contra <code>UBL-Invoice-2.1.xsd</code>, listo para descargar o probar en Nubefact.</li>
    </ol>
  </section>"""


def _aviso(aviso: Aviso) -> str:
    detalles = "".join(f"<li>{_e(d)}</li>" for d in aviso.detalles)
    campo = f" · campo <code>{_e(aviso.campo)}</code>" if aviso.campo else ""
    return f"""
  <div class="aviso" role="alert">
    <b>No se generó el XML.</b> {_e(aviso.mensaje)}
    <small>{_e(aviso.codigo)}{campo}</small>
    {f"<ul>{detalles}</ul>" if detalles else ""}
  </div>"""


def pagina_venta(formulario: FormularioVenta, *, resultado: XmlDeVenta | None = None,
                 filas: list[FilaMatriz] | None = None, aviso: Aviso | None = None,
                 emisor: str = "") -> str:
    derecha = _resultado(resultado, filas or []) if resultado else _vacio()
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Registrar venta · XML UBL 2.1</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <div>
    <h1>Registrar venta → XML UBL 2.1</h1>
    <p>{_e(emisor)} · Taller 2: el XML se genera desde las clases de <code>UBL-Invoice-2.1.xsd</code>
      con las reglas SUNAT del dominio.</p>
  </div>
  <nav><a href="/docs">API</a> · <a href="/venta">Nueva venta</a></nav>
</header>
{_aviso(aviso) if aviso else ""}
<main>
{_formulario(formulario, aviso)}
{derecha}
</main>
<script>{_JS}</script>
</body>
</html>"""


_CSS = """
:root{--fondo:#f4f6f8;--tarjeta:#fff;--texto:#1d2733;--suave:#5b6878;--borde:#d6dde5;--acento:#0b6e4f;
--acento-texto:#fff;--error:#b42318;--error-fondo:#fdecea;--ok:#0b6e4f;--codigo:#eef2f6;--marca:#e8f3ee}
@media (prefers-color-scheme:dark){:root{--fondo:#12171d;--tarjeta:#1b222b;--texto:#e6ebf0;--suave:#9aa7b4;
--borde:#2e3945;--acento:#3fb68b;--acento-texto:#0b1410;--error:#ff8a80;--error-fondo:#3a1f1f;--ok:#5fd3a6;
--codigo:#242d38;--marca:#1f3329}}
*{box-sizing:border-box}
body{margin:0;font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--fondo);
color:var(--texto)}
header{display:flex;flex-wrap:wrap;gap:8px 24px;justify-content:space-between;align-items:end;
padding:20px 24px 8px}
header h1{margin:0;font-size:1.45rem}header p{margin:4px 0 0;color:var(--suave)}
a{color:var(--acento)}
main{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:20px;padding:12px 24px 32px}
@media (max-width:1000px){main{grid-template-columns:minmax(0,1fr)}}
.tarjeta{background:var(--tarjeta);border:1px solid var(--borde);border-radius:12px;padding:18px 20px;
min-width:0}
h2{margin:0 0 12px;font-size:1.15rem;display:flex;align-items:center;gap:10px}
h3{font-size:1rem;margin:20px 0 8px}
.paso{display:inline grid;place-items:center;width:26px;height:26px;border-radius:50%;background:var(--acento);
color:var(--acento-texto);font-size:.9rem}
fieldset{border:1px solid var(--borde);border-radius:10px;margin:0 0 14px;padding:10px 14px}
legend{font-weight:600;padding:0 6px}
label{display:block;margin:6px 0;font-size:.9rem;color:var(--suave)}
label small{font-weight:normal}
.grupo{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:0 12px}
input,select,textarea{width:100%;font:inherit;color:var(--texto);background:var(--tarjeta);
border:1px solid var(--borde);border-radius:7px;padding:7px 9px;margin-top:3px}
input:disabled{color:var(--suave);background:var(--codigo)}
input:focus,select:focus,textarea:focus{outline:2px solid var(--acento);outline-offset:1px}
[aria-invalid="true"]{border-color:var(--error);background:var(--error-fondo)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.tabla-desplazable{overflow-x:auto}
table{border-collapse:collapse;width:100%}
th,td{padding:5px 6px;text-align:left;vertical-align:top;border-bottom:1px solid var(--borde)}
thead th{font-size:.8rem;color:var(--suave);font-weight:600}
.productos td{padding:4px 3px}.productos input,.productos select{margin:0;padding:6px}
.productos td:first-child{min-width:200px}.productos td:nth-child(3),.productos td:nth-child(4){min-width:90px}
.casilla{display:flex;gap:8px;align-items:center;color:var(--texto);font-size:.95rem}
.casilla input{width:auto;margin:0}
.ayuda{color:var(--suave);font-size:.84rem;margin:6px 0 10px}
button{font:inherit;border-radius:8px;padding:8px 16px;cursor:pointer;border:1px solid var(--acento)}
.principal{background:var(--acento);color:var(--acento-texto);font-weight:600}
.secundario{background:transparent;color:var(--acento)}
.quitar{border:none;background:none;color:var(--suave);font-size:1.3rem;padding:2px 8px}
.quitar:hover{color:var(--error)}
#venta .principal{width:100%;padding:11px;font-size:1.05rem;margin-top:6px}
.estado{list-style:none;padding:0;margin:0 0 14px;display:flex;flex-wrap:wrap;gap:6px}
.estado li{border:1px solid var(--borde);border-radius:999px;padding:3px 11px;font-size:.85rem}
.estado .ok{border-color:var(--ok);color:var(--ok);font-weight:600}
.dos{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;align-items:center}
@media (max-width:560px){.dos{grid-template-columns:minmax(0,1fr)}}
.importes th{font-weight:normal;color:var(--suave)}
.importes .total th,.importes .total td{font-weight:700;font-size:1.1rem;color:var(--texto)}
.letras{margin:0;padding:10px 12px;background:var(--marca);border-radius:8px;font-weight:600}
.letras small{font-weight:normal;color:var(--suave)}
details{margin-top:18px;border:1px solid var(--borde);border-radius:10px;padding:8px 12px}
summary{cursor:pointer;font-weight:600}
.matriz{font-size:.82rem}.matriz code{font-size:.78rem;word-break:break-all}
.matriz .valor{font-weight:600;word-break:break-word}
.o{font-size:.7rem;border:1px solid var(--suave);border-radius:4px;padding:0 3px;color:var(--suave)}
code{background:var(--codigo);border-radius:4px;padding:0 4px}
.acciones{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
textarea{height:340px;font:12.5px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre;
overflow:auto;margin-top:8px}
.aviso{margin:8px 24px 0;padding:12px 16px;border:1px solid var(--error);background:var(--error-fondo);
border-radius:10px;color:var(--texto)}
.aviso small{display:block;color:var(--suave);margin-top:4px}.aviso ul{margin:6px 0 0}
.vacio ol{color:var(--suave)}
"""

_JS = """
(function(){
  var filas=document.getElementById('filas'),plantilla=document.getElementById('plantilla-fila');
  document.getElementById('agregar').addEventListener('click',function(){
    filas.appendChild(plantilla.content.firstElementChild.cloneNode(true));
    filas.lastElementChild.querySelector('input').focus();
  });
  filas.addEventListener('click',function(ev){
    if(!ev.target.classList.contains('quitar'))return;
    if(filas.children.length>1){ev.target.closest('tr').remove();}
  });
  var tipo=document.getElementById('tipo'),serie=document.getElementById('serie');
  tipo.addEventListener('change',function(){
    var letra=tipo.value==='03'?'B':'F';
    if(/^[FB][A-Z0-9]{3}$/.test(serie.value)){serie.value=letra+serie.value.slice(1);}
  });
  serie.addEventListener('input',function(){serie.value=serie.value.toUpperCase();});
  var xml=document.getElementById('xml');
  if(!xml)return;
  document.getElementById('descargar').addEventListener('click',function(ev){
    var enlace=document.createElement('a');
    enlace.href=URL.createObjectURL(new Blob([xml.value],{type:'application/xml'}));
    enlace.download=ev.target.dataset.nombre;
    document.body.appendChild(enlace);enlace.click();enlace.remove();
    setTimeout(function(){URL.revokeObjectURL(enlace.href);},1000);
  });
  document.getElementById('copiar').addEventListener('click',function(ev){
    var boton=ev.target,listo=function(){boton.textContent='Copiado ✓';
      setTimeout(function(){boton.textContent='Copiar XML';},1500);};
    if(navigator.clipboard){navigator.clipboard.writeText(xml.value).then(listo,function(){xml.select();});}
    else{xml.select();document.execCommand('copy');listo();}
  });
})();
"""
