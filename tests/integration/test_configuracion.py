"""Producción nunca arranca con los tokens de desarrollo.

Los tokens ``dev-*`` están publicados en el README: si ``ABC_API_TOKENS`` faltara en producción,
``dev-facturador`` (todos los alcances) emitiría comprobantes reales ante SUNAT.
"""

from __future__ import annotations

import json

import pytest

from src.adapters.outbound.ose.sunat_soap import ENDPOINT_BETA, ENDPOINT_PRODUCCION
from src.config import TOKENS_DESARROLLO, Configuracion, es_token_de_desarrollo

PRODUCCION = {"sunat_endpoint": ENDPOINT_PRODUCCION, "sunat_usuario_sol": "20556677884FACTURA1"}
TOKENS_PROPIOS = {"token-largo-y-secreto": frozenset({"comprobantes:leer"})}


def test_produccion_rechaza_los_tokens_de_desarrollo_por_defecto(tmp_path):
    with pytest.raises(ValueError, match="dev-"):
        Configuracion(certificado_pfx=tmp_path / "emisor.pfx", **PRODUCCION)


@pytest.mark.parametrize("token", ["dev-facturador", "dev-otro-inventado"])
def test_produccion_rechaza_un_token_dev_mezclado_con_tokens_propios(tmp_path, token):
    tokens = {**TOKENS_PROPIOS, token: frozenset({"libros:leer"})}
    with pytest.raises(ValueError, match="dev-"):
        Configuracion(certificado_pfx=tmp_path / "emisor.pfx", tokens=tokens, **PRODUCCION)


def test_produccion_rechaza_quedarse_sin_tokens(tmp_path):
    with pytest.raises(ValueError, match="ABC_API_TOKENS"):
        Configuracion(certificado_pfx=tmp_path / "emisor.pfx", tokens={}, **PRODUCCION)


def test_produccion_acepta_tokens_propios(tmp_path):
    configuracion = Configuracion(certificado_pfx=tmp_path / "emisor.pfx", tokens=TOKENS_PROPIOS, **PRODUCCION)
    assert not any(es_token_de_desarrollo(t) for t in configuracion.tokens)


def test_produccion_sin_abc_api_tokens_no_arranca(monkeypatch, tmp_path):
    monkeypatch.setenv("ABC_SUNAT_ENDPOINT", "produccion")
    monkeypatch.setenv("ABC_CERTIFICADO_PFX", str(tmp_path / "emisor.pfx"))
    monkeypatch.setenv("ABC_SUNAT_USUARIO_SOL", PRODUCCION["sunat_usuario_sol"])
    monkeypatch.delenv("ABC_API_TOKENS", raising=False)
    with pytest.raises(ValueError, match="dev-"):
        Configuracion.desde_entorno()

    monkeypatch.setenv("ABC_API_TOKENS", json.dumps({"token-largo-y-secreto": ["comprobantes:emitir"]}))
    assert set(Configuracion.desde_entorno().tokens) == {"token-largo-y-secreto"}


@pytest.mark.parametrize("endpoint", [None, ENDPOINT_BETA])
def test_desarrollo_y_beta_conservan_los_tokens_de_desarrollo(endpoint):
    assert Configuracion(sunat_endpoint=endpoint).tokens == TOKENS_DESARROLLO
