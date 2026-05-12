#!/usr/bin/env bash
# Cria o ambiente virtual e instala dependências (uma vez por máquina ou após clone).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Criando .venv com $(command -v python3)..."
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -r requirements.txt
echo "Pronto. export PYTHONPATH=\"$ROOT/src\" ou use os scripts em ./scripts/ (eles definem PYTHONPATH)."
echo "Ex.: ./scripts/relacionar_arquivos_estatais.sh | ./scripts/preencher_planilha_estatais.sh"
