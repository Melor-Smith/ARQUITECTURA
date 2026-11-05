"""Adaptador ``Reloj`` con la hora de Perú (UTC-5, sin horario de verano)."""

from __future__ import annotations

import datetime as dt

ZONA_PERU = dt.timezone(dt.timedelta(hours=-5), "America/Lima")


class RelojSistema:
    def ahora(self) -> dt.datetime:
        return dt.datetime.now(ZONA_PERU)


class RelojFijo:
    """Útil en pruebas y demostraciones reproducibles."""

    def __init__(self, instante: dt.datetime) -> None:
        self.instante = instante if instante.tzinfo else instante.replace(tzinfo=ZONA_PERU)

    def ahora(self) -> dt.datetime:
        return self.instante
