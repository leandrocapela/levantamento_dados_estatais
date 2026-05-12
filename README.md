# Levantamento de dados — ACT e PCS (estatais)

Ferramentas em **Python** para extrair texto de PDFs (PyMuPDF), aplicar **regex** e relacionar arquivos à coluna **ESTATAL** da planilha mestre. Não substitui revisão humana do instrumento coletivo.

## Estrutura do repositório

```
├── config/                 # YAML de ligação arquivo ↔ estatal
├── data/
│   ├── docs/
│   │   ├── acordos_coletivos_trabalho/   # PDFs de acordo coletivo de trabalho
│   │   └── planos_cargos_salarios/       # PDFs de plano de cargos e salários
│   └── planilhas/          # Dados Estatais.xlsx, dicionário
├── output/                 # Excel gerados (não versionar por defeito; ver .gitignore)
├── scripts/                # Atalhos shell (definem PYTHONPATH)
├── src/levantamento_dados_estatais/   # Código do pacote
├── requirements.txt
└── README.md
```

Os scripts assumem `PYTHONPATH=<raiz>/src` e correm módulos com `python -m levantamento_dados_estatais.…`.

## Instalação

```bash
cd levantamento_dados_estatais
./scripts/instalar.sh
```

Ou manualmente: `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`.

## Uso (scripts)

```bash
./scripts/extrair_act_pcs.sh --pdf "data/docs/acordos_coletivos_trabalho/BNDES - Proposta ACT 2024-2026 - vfinal.pdf"
./scripts/pipeline_extracao.sh
./scripts/relacionar_arquivos_estatais.sh
./scripts/preencher_planilha_estatais.sh
```

Equivalente sem shell: `export PYTHONPATH="$(pwd)/src"` e `python -m levantamento_dados_estatais.extrair_act_pcs …`.

### Módulos

| Comando | Descrição |
|---------|-----------|
| `levantamento_dados_estatais.extrair_act_pcs` | JSON com `niv_carreira`, `tem_ats`, `tipo_ats`, `ano_pcs` por PDF |
| `levantamento_dados_estatais.pipeline_extracao` | Lote de PDFs → Excel (`output/extracao_pdf_regex.xlsx` por defeito) |
| `levantamento_dados_estatais.relacionar_arquivos_estatais` | `output/mapeamento_arquivos_estatais.xlsx` |
| `levantamento_dados_estatais.preencher_planilha_estatais` | Lê `data/planilhas/Dados Estatais.xlsx` → `output/Dados_Estatais_preenchido_auto.xlsx` |

Opções de pastas (por defeito vêm de `caminhos_projeto.py`, pastas em disco `data/docs/…`): `--pasta-documentos-acordos-coletivos-trabalho`, `--pasta-documentos-planos-cargos-salarios`.

### `tem_ats` (conservador)

- **`SIM`**: há menção explícita no texto (anuênio, quinquênio, ATS, “adicional por tempo de serviço”).
- **`NÃO`**: só quando há **cláusula explícita** de inexistência/supressão (padrões em `pipeline_extracao.py`); **não** se infere por ausência de palavras-chave.
- **`null`** (JSON) / célula vazia (planilha): texto não permite concluir.

### PREVISÃO DO ATS (planilha preenchida)

Cada evidência é uma linha com **origem** (`ACT` ou `PCS`), **nome do arquivo** e o texto extraído (regra ATS ou tipo).

### Configuração `config/estatal_arquivo_config.yaml`

1. `arquivo_para_estatal` — nome exacto do PDF → ESTATAL (só quando confirmado).
2. `substrings` — gatilhos no nome do arquivo; até 4 caracteres usam limite de “palavra”.
3. Fuzzy (opcional) com limiar `--fuzzy-min`; estatais com nome muito curto (≤4 caracteres após normalização) não entram no fuzzy.

**NPCS** (Novo Plano de Cargos e Salários): o PDF `NPCS_2025_versão+site_com+regulamento.pdf` está mapeado para **BNDES** no YAML.

## Desenvolvimento

Pacote `levantamento_dados_estatais`: `pipeline_extracao`, `estatal_matching`, `caminhos_projeto`, CLIs em `relacionar_arquivos_estatais.py`, `preencher_planilha_estatais.py`, `extrair_act_pcs.py`.

---

*Contexto: GT de Cargos e Salários / levantamento em empresas estatais.*
