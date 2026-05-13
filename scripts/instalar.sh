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
if ! command -v tesseract &>/dev/null; then
  echo "Aviso: comando 'tesseract' não encontrado no PATH."
  if [[ "$(uname -s)" == "Darwin" ]] && command -v brew &>/dev/null; then
    PREFIX="$(brew --prefix tesseract 2>/dev/null || true)"
    if [[ -n "${PREFIX:-}" && -x "${PREFIX}/bin/tesseract" ]]; then
      echo "      Binário provável do Homebrew: ${PREFIX}/bin/tesseract"
      echo "      No Cursor, use: export LEV_DADOS_TESSERACT_CMD=\"${PREFIX}/bin/tesseract\""
    fi
  fi
  echo "      Instalação típica: brew install tesseract tesseract-lang"
fi
echo "Pronto. export PYTHONPATH=\"$ROOT/src\" ou use os scripts em ./scripts/ (eles definem PYTHONPATH)."
echo "Ex.: ./scripts/relacionar_arquivos_estatais.sh | ./scripts/preencher_planilha_estatais.sh"
if [[ ! -f "$ROOT/.env" ]]; then
  echo "PDFs fora do repo (Drive, etc.): cp .env.example .env e defina LEV_DADOS_PASTA_ACT / LEV_DADOS_PASTA_PCS (ver README)."
fi
