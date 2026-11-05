"""Vistas de los libros electrónicos: TXT del PLE y JSON.

El contenido del TXT (orden, formato y validación de cada campo según el Anexo 2) lo
produce el dominio (``ple_estructura``); esta vista solo lo empaqueta como respuesta HTTP.
"""

from __future__ import annotations

from fastapi.responses import Response

from src.adapters.inbound.http.esquemas import LibroElectronicoSalida
from src.domain.libros import FilaInventario121, LibroElectronico
from src.domain.ple_estructura import ESTRUCTURAS, Campo, TipoDato, contenido_txt, formatear

#: Saldo del Kardex: no va en el TXT, pero sí en la vista JSON (formato impreso del 12.1).
_SALDO = Campo(0, "saldo_final", "Saldo final", TipoDato.IMPORTE, 12, False)


def libro_txt(libro: LibroElectronico) -> Response:
    return Response(
        content=contenido_txt(libro.identificador, libro.filas).encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{libro.nombre_archivo}"'},
    )


def libro_json(formato: str, libro: LibroElectronico) -> LibroElectronicoSalida:
    estructura = ESTRUCTURAS[libro.identificador]
    contenido_txt(libro.identificador, libro.filas)  # mismas validaciones que el TXT

    def campos(fila: object) -> dict[str, str]:
        datos = {c.atributo: formatear(c, getattr(fila, c.atributo)) for c in estructura}
        if isinstance(fila, FilaInventario121):
            datos[_SALDO.atributo] = formatear(_SALDO, fila.saldo_final)
        return datos

    return LibroElectronicoSalida(
        formato=formato, nombre_archivo=libro.nombre_archivo, periodo=str(libro.periodo),
        filas=[campos(f) for f in libro.filas],
    )
