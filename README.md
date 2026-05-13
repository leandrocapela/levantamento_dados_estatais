# Levantamento de dados — ACT e PCS (estatais)

Ferramentas em **Python** para análise **aprofundada** de **estatais selecionadas** (trabalho individual, não painel macro de dezenas de empresas). Extrai texto de PDFs (**PyMuPDF**; em páginas escaneadas usa **OCR com Tesseract**), aplica **regex** e heurísticas e relaciona arquivos à coluna **ESTATAL** da planilha mestre.

**Foco de extração (ACT e PCS):** três pilares de remuneração — **salário base** (grade, piso, teto, amplitude), **ATS** (percentuais, periodicidade anuênio/quinquênio, menções a teto acumulado) e **gratificações** (função, atividade, titularidade; valores ou percentuais). O refinamento contínuo vive em `pipeline_extracao.py`; a saída `Dados_Estatais_preenchido_auto.xlsx` agrega evidências na **PREVISÃO DO ATS** e em **PERCENTUAL** quando a coluna existir. Não substitui revisão humana do instrumento coletivo.

## Estrutura do repositório

```
├── config/
│   └── estatal_arquivo_config.yaml   # Gatilhos substrings → ESTATAL
├── data/
│   ├── docs/
│   │   ├── acordos_coletivos_trabalho/   # PDFs de ACT
│   │   └── planos_cargos_salarios/       # PDFs de PCS
│   └── planilhas/
│       ├── Dados Estatais.xlsx           # Planilha mestre
│       └── Dicionário de Dados Estatais.xlsx
├── output/                 # Excel gerados (não versionar por padrão; ver .gitignore)
│   ├── mapeamento_arquivos_estatais.xlsx
│   ├── Dados_Estatais_preenchido_auto.xlsx
│   └── extracao_pdf_regex.xlsx
├── scripts/                # Atalhos shell (venv + PYTHONPATH)
├── src/levantamento_dados_estatais/
├── AGENTS.md               # Contexto do projeto e convenções de código (para o agente)
├── requirements.txt
└── README.md
```

Caminhos padrão são centralizados em `caminhos_projeto.py` (`RAIZ_REPOSITORIO`, pastas sob `data/`, `config/`, `output/`).

## Layout de dados

| Caminho | Uso |
|--------|-----|
| `data/planilhas/` | Entrada: `Dados Estatais.xlsx` (coluna **ESTATAL**; opcionalmente **Dicionário de Dados Estatais.xlsx**) |
| `data/docs/acordos_coletivos_trabalho/` | PDFs de ACT |
| `data/docs/planos_cargos_salarios/` | PDFs de PCS |
| `config/estatal_arquivo_config.yaml` | Mapa **substrings** (chaves = valores de **ESTATAL** iguais à planilha) |

### PDFs no Google Drive e trabalho em equipe

O código **não** chama a API do Drive: só precisa de **pastas locais**. Para quem entra no projeto fazer o mínimo de passos:

1. **Alinhamento na equipe (uma vez)**  
   - No Drive: pasta compartilhada com subpastas estáveis **`ACT`** e **`PCS`** (ou nomes iguais aos que documentarem).  
   - Se a pasta estiver só em **Compartilhados comigo**, criem um **atalho no “Meu Drive”** (ex.: `Meu Drive/LevantamentoEstatais/ACT` e `…/PCS`) para o caminho ser o mesmo para toda a gente e fácil de descrever.

2. **Cada máquina (uma vez)**  
   - Instalar **Google Drive para desktop** e garantir que essas pastas estão sincronizadas / visíveis no disco.
   - `cp .env.example .env`  
   - Editar `.env`: definir **`LEV_DADOS_PASTA_ACT`** e **`LEV_DADOS_PASTA_PCS`** com caminhos **absolutos** até às pastas dos PDFs (ver comentários em `.env.example`).  
   - O arquivo `.env` **não vai para o git** (`.gitignore`).

3. **Correr os scripts**  
   - `./scripts/relacionar_arquivos_estatais.sh` e `./scripts/preencher_planilha_estatais.sh` leem `.env` automaticamente e passam `--pasta-docs-...`.  
   - Se na linha de comando passarem de novo `--pasta-docs-...`, esse valor **substitui** o do arquivo (útil para testes).

## `relacionar_arquivos_estatais`

Gera **`output/mapeamento_arquivos_estatais.xlsx`**: uma **linha por PDF** (formato longo), com colunas `tipo` (`ACT` ou `PCS`), `pasta`, `arquivo`, `estatal` (ou vazio) e **`metodo_match`**:

- `substring` — gatilho de `substrings` no **nome** do arquivo (substring mais longa vence);
- `fuzzy` — `rapidfuzz.partial_ratio` entre nome da estatal e nome do arquivo (limiar `--fuzzy-min`, padrão 88; estatais com nome muito curto após normalização não entram);
- `texto_pdf` — mesmos gatilhos sobre texto extraído do PDF (nativo + OCR quando necessário; **até 12 primeiras páginas** neste fluxo);
- `none` — sem correspondência.

## `config/estatal_arquivo_config.yaml`

Só o bloco **`substrings`** (estatal → lista de gatilhos). Não há outro mapeamento no YAML; os mesmos gatilhos servem para nome e para corpo.

Ordem no código (`estatal_matching`):

1. **Nome do arquivo** — o gatilho mais longo que bater ganha; gatilhos curtos (≤4 caracteres após normalização) usam limite de “palavra”.
2. **Fuzzy só no nome** — limiar `--fuzzy-min`; estatais com nome muito curto não entram no fuzzy.
3. **Texto do PDF** — `extrair_texto_pdf` (camada nativa + OCR por página quando o texto nativo é escasso), **até 12 páginas** neste passo, e de novo os **mesmos** gatilhos sobre o texto reunido.

Inclua no YAML tanto trechos típicos de nomes de arquivo como frases que só aparecem no corpo (ex.: PDF com nome genérico mas corpo com “banco nacional de desenvolvimento…” → **BNDES**).

## `preencher_planilha_estatais`

Lê **`data/planilhas/Dados Estatais.xlsx`** e escreve **`output/Dados_Estatais_preenchido_auto.xlsx`**.

- Colunas **ACT** e **PCS**: **sempre** um único nome de arquivo (o de melhor match: substring, depois fuzzy, depois texto no PDF; empate pelo nome). Outros PDFs que casaram com a mesma estatal continuam a ser usados só na extração dos demais campos.
- Demais colunas derivadas dos PDFs (**níveis de carreira**, **TEM ATS?**, **anuênio/quinquênio**, **ano do PCS**, **PREVISÃO DO ATS**) só são escritas **onde a célula está vazia** (ver docstring do módulo para prioridade ACT vs PCS e regras de **TEM ATS?**).

## Instalação

```bash
cd levantamento_dados_estatais
./scripts/instalar.sh
```

Ou manualmente: `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`.

### PDF escaneado (OCR)

Quando uma página quase não tem texto selecionável, o código tenta **OCR (Tesseract)**. O limite de páginas em que o OCR é aplicado (para páginas “vazias”) está em `pdf_texto` (padrão **25** no recorte). No **pipeline** em lote, o texto pode percorrer o documento inteiro (`max_paginas=None`); no **match por estatal**, a leitura para gatilhos no corpo limita-se às **12** primeiras páginas.

Instale o binário no sistema (além do `pip`):

- **macOS:** `brew install tesseract tesseract-lang`
- **Debian/Ubuntu:** `sudo apt install tesseract-ocr tesseract-ocr-por`

O **Cursor** (e alguns outros ambientes) muitas vezes **não colocam** `/opt/homebrew/bin` no `PATH`. O código tenta sozinho `/opt/homebrew/bin/tesseract` e `/usr/local/bin/tesseract`. Se ainda falhar, defina o caminho completo:

```bash
export LEV_DADOS_TESSERACT_CMD="/opt/homebrew/bin/tesseract"
```

O código também reconhece `TESSERACT_CMD`.

Para desligar o OCR (só camada nativa): `export LEV_DADOS_PDF_OCR=0`.

## Como executar

Os scripts em `scripts/` exigem **`.venv`** criado (`./scripts/instalar.sh`), ativam o venv e definem `PYTHONPATH=<raiz>/src`. Alternativa manual: `source .venv/bin/activate` e `export PYTHONPATH="$(pwd)/src"`, depois `python -m levantamento_dados_estatais.<módulo> …`.

```bash
./scripts/extrair_act_pcs.sh --pdf "data/docs/acordos_coletivos_trabalho/exemplo.pdf"
./scripts/pipeline_extracao.sh
./scripts/relacionar_arquivos_estatais.sh
./scripts/preencher_planilha_estatais.sh
./scripts/testar_ocr_pdf.sh --help   # diagnóstico nativo vs OCR num PDF
```

### Módulos

| Comando | Descrição |
|---------|-----------|
| `levantamento_dados_estatais.extrair_act_pcs` | JSON com campos de carreira/ATS/ano PCS e **pilares** (`salario_grade_resumo`, `ats_percentual`, `ats_teto_resumo`, `gratificacoes_resumo`) por PDF |
| `levantamento_dados_estatais.pipeline_extracao` | Lote de PDFs → `output/extracao_pdf_regex.xlsx` (mesmas colunas heurísticas) |
| `levantamento_dados_estatais.relacionar_arquivos_estatais` | Uma linha por PDF → `output/mapeamento_arquivos_estatais.xlsx` |
| `levantamento_dados_estatais.preencher_planilha_estatais` | Planilha mestre → `output/Dados_Estatais_preenchido_auto.xlsx` |
| `levantamento_dados_estatais.testar_ocr_pdf` | Teste de extração nativa vs com OCR |

Opções de pastas (padrão em `caminhos_projeto.py`): `--pasta-docs-acordos-coletivos-trabalho`, `--pasta-docs-planos-cargos-salarios`.

### `tem_ats` (conservador)

- **`SIM`**: há menção explícita no texto (anuênio, quinquênio, ATS, “adicional por tempo de serviço”).
- **`NÃO`**: só quando há **cláusula explícita** de inexistência/supressão (padrões em `pipeline_extracao.py`); **não** se infere por ausência de palavras-chave.
- **`null`** (JSON) / célula vazia (planilha): texto não permite concluir.

### PREVISÃO DO ATS (planilha preenchida)

Inclui linhas clássicas (regra/tipo ATS) e blocos **[Salário base]**, **[ATS]** (% e teto quando encontrados) e **[Gratificações]** por arquivo. A coluna **PERCENTUAL** é preenchida se existir na planilha (primeiro % de ATS inferido, PCS antes de ACT).

## Desenvolvimento

Pacote `levantamento_dados_estatais`: `pdf_texto`, `pipeline_extracao`, `estatal_matching`, `caminhos_projeto`, CLIs em `relacionar_arquivos_estatais.py`, `preencher_planilha_estatais.py`, `extrair_act_pcs.py`, `testar_ocr_pdf.py`.

---

*Contexto: GT de Cargos e Salários / levantamento em empresas estatais.*
