"""Raiz do repositório e caminhos convencionais (dados, configuração, saídas)."""
from __future__ import annotations

from pathlib import Path

# Três níveis acima deste arquivo = raiz do repositório (src/<pacote>/caminhos_projeto.py)
RAIZ_REPOSITORIO: Path = Path(__file__).resolve().parent.parent.parent

PASTA_CONFIGURACAO: Path = RAIZ_REPOSITORIO / "config"
ARQUIVO_CONFIGURACAO_ESTATAIS_PADRAO: Path = PASTA_CONFIGURACAO / "estatal_arquivo_config.yaml"

PASTA_DADOS: Path = RAIZ_REPOSITORIO / "data"
PASTA_DOCS_ACORDOS_COLETIVOS_TRABALHO: Path = (
    PASTA_DADOS / "docs" / "acordos_coletivos_trabalho"
)
PASTA_DOCS_PLANOS_CARGOS_SALARIOS: Path = (
    PASTA_DADOS / "docs" / "planos_cargos_salarios"
)
PASTA_PLANILHAS: Path = PASTA_DADOS / "planilhas"
ARQUIVO_PLANILHA_DADOS_ESTATAIS: Path = PASTA_PLANILHAS / "Dados Estatais.xlsx"
ARQUIVO_PLANILHA_DICIONARIO_DADOS_ESTATAIS: Path = (
    PASTA_PLANILHAS / "Dicionário de Dados Estatais.xlsx"
)

DIRETORIO_OUTPUT: Path = RAIZ_REPOSITORIO / "output"
ARQUIVO_SAIDA_MAPEAMENTO_ARQUIVOS_ESTATAIS: Path = (
    DIRETORIO_OUTPUT / "mapeamento_arquivos_estatais.xlsx"
)
ARQUIVO_SAIDA_PLANILHA_DADOS_ESTATAIS_PREENCHIDA_AUTOMATICAMENTE: Path = (
    DIRETORIO_OUTPUT / "Dados_Estatais_preenchido_auto.xlsx"
)
ARQUIVO_SAIDA_EXTRACAO_PIPELINE_REGEX: Path = (
    DIRETORIO_OUTPUT / "extracao_pdf_regex.xlsx"
)
