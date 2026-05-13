#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT/src"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  echo "Execute primeiro: ./scripts/instalar.sh" >&2
  exit 1
fi
# shellcheck source=/dev/null
source .venv/bin/activate
# shellcheck source=pastas_locais.inc.sh
source "$ROOT/scripts/pastas_locais.inc.sh"
# Bash 3.2 (macOS) + set -u: "${arr[@]}" com array vazio falha; usar expansão condicional.
exec python -m levantamento_dados_estatais.preencher_planilha_estatais ${LEV_DADOS_EXTRA_PASTAS[@]+"${LEV_DADOS_EXTRA_PASTAS[@]}"} "$@"
