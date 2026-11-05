# Renderiza cada docs/diagramas/*.mmd a .svg y .png con Mermaid CLI (versión fijada).
# Uso (Windows, con Node.js 18+):  powershell -ExecutionPolicy Bypass -File scripts/renderizar_diagramas.ps1
# tests/integration/test_diagramas.py falla si un .mmd no tiene su .svg y su .png al día.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$mmdc = "@mermaid-js/mermaid-cli@11.4.2"
Get-ChildItem "$raiz/docs/diagramas/*.mmd" | ForEach-Object {
    $base = Join-Path $_.DirectoryName $_.BaseName
    Write-Host "Renderizando $($_.Name)"
    npx -y $mmdc -i $_.FullName -o "$base.svg" -b white
    if ($LASTEXITCODE -ne 0) { throw "Mermaid no pudo renderizar $($_.Name)" }
    npx -y $mmdc -i $_.FullName -o "$base.png" -b white -s 2
    if ($LASTEXITCODE -ne 0) { throw "Mermaid no pudo renderizar $($_.Name)" }
}
