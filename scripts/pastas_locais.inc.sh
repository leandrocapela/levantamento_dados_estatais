# Incluir a partir de scripts/*.sh depois de definir ROOT (raiz do repositório).
# Carrega .env na raiz do repositório se existir e define LEV_DADOS_EXTRA_PASTAS para passar ao Python.

LEV_DADOS_EXTRA_PASTAS=()
if [[ -n "${ROOT:-}" && -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi
if [[ -n "${LEV_DADOS_PASTA_ACT:-}" ]]; then
  LEV_DADOS_EXTRA_PASTAS+=(--pasta-docs-acordos-coletivos-trabalho "$LEV_DADOS_PASTA_ACT")
fi
if [[ -n "${LEV_DADOS_PASTA_PCS:-}" ]]; then
  LEV_DADOS_EXTRA_PASTAS+=(--pasta-docs-planos-cargos-salarios "$LEV_DADOS_PASTA_PCS")
fi
