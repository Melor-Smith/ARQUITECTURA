#!/usr/bin/env sh
# Renderiza cada docs/diagramas/*.mmd a .svg y .png con Mermaid CLI (versión fijada).
# Uso (Linux/macOS o la CI, con Node.js 18+):  sh scripts/renderizar_diagramas.sh
# tests/integration/test_diagramas.py falla si un .mmd no tiene su .svg y su .png al día.
set -eu
raiz="$(cd "$(dirname "$0")/.." && pwd)"
mmdc="@mermaid-js/mermaid-cli@11.4.2"
for fuente in "$raiz"/docs/diagramas/*.mmd; do
  base="${fuente%.mmd}"
  echo "Renderizando $(basename "$fuente")"
  npx -y "$mmdc" -i "$fuente" -o "$base.svg" -b white ${MMDC_PUPPETEER:+-p "$MMDC_PUPPETEER"}
  npx -y "$mmdc" -i "$fuente" -o "$base.png" -b white -s 2 ${MMDC_PUPPETEER:+-p "$MMDC_PUPPETEER"}
done
