#!/usr/bin/env sh
# Regenera las clases Python tipadas desde los XSD oficiales OASIS UBL 2.1.
# Requiere: pip install -r requirements-dev.txt
set -e
cd "$(dirname "$0")/.."
xsdata generate specs/contracts/ubl-2.1/xsd/maindoc --package src.adapters.outbound.ubl.generated
