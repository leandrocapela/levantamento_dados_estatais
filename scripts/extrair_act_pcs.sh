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
exec python -m levantamento_dados_estatais.extrair_act_pcs "$@"
