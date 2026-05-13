# Contexto do projeto (para o agente)

Define **domínio**, **entradas principais** e **fluxos** deste repositório para orientar alterações e leitura de código.

## O que é

Levantamento de dados a partir de PDFs de **ACT** e **PCS** para **estatais selecionadas**, em visão **individual** (análise aprofundada, não cobertura macro de muitas empresas). Alinhamento à coluna **ESTATAL** em `data/planilhas/Dados Estatais.xlsx`.

**Prioridade de extração:** três pilares de remuneração, com regex e heurísticas em **`pipeline_extracao.py`** (refino contínuo):

1. **Salário base** — grade (níveis/steps), piso, teto, amplitude quando o texto permitir inferência segura.
2. **ATS** — periodicidade (anuênio/quinquênio), percentuais, indícios de **teto acumulado** ou limite de incorporação.
3. **Gratificações** — gratificação de **função**, **atividade** ou **titularidade** (e análogos), com valor ou percentual quando aparecerem no corpo (incluindo trechos compactos tipo nota de rodapé — busca em texto normalizado e janelas largas).

**Saída para projeções:** `preencher_planilha_estatais.py` incorpora evidências desses pilares na **PREVISÃO DO ATS (PCS OU ACT)** e preenche **PERCENTUAL** se a coluna existir na planilha. `estatal_matching.py` continua a ligar PDF → estatal.

## Onde está o quê

- **Caminhos padrão:** `src/levantamento_dados_estatais/caminhos_projeto.py` (`RAIZ_REPOSITORIO`, `data/docs/...`, `config/`, `output/`).
- **Match PDF → estatal:** `config/estatal_arquivo_config.yaml` (só `substrings`); lógica em `estatal_matching.py` (nome → fuzzy no nome → texto do PDF até 12 páginas).
- **Preencher planilha:** `preencher_planilha_estatais.py` — colunas ACT/PCS (um arquivo representativo por tipo); demais colunas só onde vazio; lê `.env` na raiz para pastas de PDFs quando os scripts shell carregam `pastas_locais.inc.sh`.
- **Mapeamento longo:** `relacionar_arquivos_estatais.py` → `output/mapeamento_arquivos_estatais.xlsx`.

## Execução típica

- `./scripts/instalar.sh` — cria `.venv` e instala dependências.
- Copiar `.env.example` → `.env` e definir `LEV_DADOS_PASTA_ACT` / `LEV_DADOS_PASTA_PCS` se os PDFs não estiverem em `data/docs/...`.
- `./scripts/relacionar_arquivos_estatais.sh` e `./scripts/preencher_planilha_estatais.sh` — leem `.env` via `scripts/pastas_locais.inc.sh`.

## Convenções (código e texto)

### Projeto e layout

- Pacote principal: `levantamento_dados_estatais` sob `src/`.
- PDFs em `data/docs/` podem não existir no clone; usar `.env` ou cópia local conforme o `README.md`.

### Nomenclatura

- Evitar **abreviações** em nomes de variáveis, funções, módulos e identificadores públicos; preferir nomes **descritivos** e legíveis.
- **Exceção** já usada no repositório: diretórios chamados **`output`** e **`docs`** (na raiz ou sob `data/`) mantêm esses nomes curtos.

### Idioma na prosa do código

- Comentários e **docstrings** em **português do Brasil**; em prosa, o equivalente a *file* é **arquivo**.
- **Identificadores** (funções, classes, variáveis) e nomes de módulos podem ficar em **inglês** quando for mais claro ou alinhado ao que já existe (`Path`, `MatchResult`, `fold_for_match`).

### Python

- Manter `from __future__ import annotations` nos módulos que já usam; adotar o mesmo em módulos novos.
- Tipagem nas funções e métodos **públicos** novos; nos arquivos antigos, seguir o **mesmo nível** de anotações que o restante do arquivo.
- Preferir **`pathlib.Path`** para caminhos em código novo quando o módulo já trabalha com `Path`.
- CLIs com **`argparse`**; constantes de domínio em **MAIÚSCULAS** no estilo existente (`COL_ACT`, `PASTA_DOCS_...`).

### Alterações

- Difs **pequenos** e alinhados ao estilo do arquivo (ordem de imports, formatação, quantidade de comentários).
- Evitar refatorações largas ou arquivos novos não pedidos para a tarefa.
