"""Prueba de contrato EN VIVO contra el servicio beta de SUNAT.

Se omite por defecto: depende de la red y de la disponibilidad de SUNAT, y la CI principal
debe ser determinista. Se ejecuta con ``ABC_SUNAT_BETA_EN_VIVO=1`` y en el workflow
``.github/workflows/sunat-beta.yml`` (a demanda y semanal). La versión sin red, sobre
respuestas reales grabadas, está en ``test_cliente_sunat_soap.py`` y ``test_evidencia_sunat.py``.
"""

from __future__ import annotations

import os

import pytest

from scripts.validar_en_sunat_beta import validar

pytestmark = pytest.mark.skipif(os.environ.get("ABC_SUNAT_BETA_EN_VIVO") != "1",
                                reason="prueba en vivo: defina ABC_SUNAT_BETA_EN_VIVO=1")


def test_sunat_beta_acepta_los_siete_comprobantes_del_caso():
    resultados, enviados, respuestas = validar()
    assert [(r["comprobante"], r["estado"], (r["cdr"] or {}).get("codigo")) for r in resultados] == [
        (r["comprobante"], "ACEPTADO", "0") for r in resultados]
    assert len(resultados) == len(enviados) == len(respuestas) == 7
