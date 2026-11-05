"""Fixtures compartidas. Cada prueba arma su propio contenedor: no hay estado global."""

from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.adapters.inbound.http.app import crear_app
from src.adapters.outbound.reloj import ZONA_PERU, RelojFijo
from src.bootstrap import construir_contenedor
from src.config import Configuracion

RAIZ = Path(__file__).resolve().parents[1]
EJEMPLOS = RAIZ / "specs" / "ejemplos"
AHORA = dt.datetime(2026, 10, 22, 10, 30, tzinfo=ZONA_PERU)

FACTURADOR = {"Authorization": "Bearer dev-facturador"}
ALMACEN = {"Authorization": "Bearer dev-almacen"}
CONSULTA = {"Authorization": "Bearer dev-consulta"}

URL_COMPROBANTES = "/api/v1/comprobantes"
URL_MIGRACIONES = "/api/v1/inventario/migraciones"


def ejemplo(nombre: str) -> dict:
    """Copia profunda de un ejemplo del contrato (``specs/ejemplos``)."""
    return copy.deepcopy(json.loads((EJEMPLOS / nombre).read_text(encoding="utf-8")))


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo(AHORA)


@pytest.fixture
def contenedor(reloj):
    return construir_contenedor(Configuracion(), reloj=reloj)


@pytest.fixture
def cliente(contenedor) -> TestClient:
    return TestClient(crear_app(contenedor))


@pytest.fixture
def emitir(cliente):
    def _emitir(payload: dict, headers: dict | None = None):
        return cliente.post(URL_COMPROBANTES, json=payload, headers=headers or FACTURADOR)

    return _emitir


@pytest.fixture
def migrar(cliente):
    def _migrar(payload: dict, headers: dict | None = None):
        return cliente.post(URL_MIGRACIONES, json=payload, headers=headers or ALMACEN)

    return _migrar
