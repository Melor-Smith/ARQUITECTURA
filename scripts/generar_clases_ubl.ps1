# Regenera las clases Python tipadas desde los XSD oficiales OASIS UBL 2.1.
# Requiere: pip install -r requirements-dev.txt
Set-Location (Join-Path $PSScriptRoot "..")
xsdata generate specs/contracts/ubl-2.1/xsd/maindoc --package src.adapters.outbound.ubl.generated
