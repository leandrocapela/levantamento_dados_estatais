"""
Relaciona nomes de arquivos PDF (ACT / PCS) à coluna ESTATAL de Dados Estatais.xlsx.

Ordem de decisão (simples):
1. Mesmos gatilhos de `substrings` no **nome** do arquivo (substring mais longa ganha).
2. Se não bater: **fuzzy** só no nome (partial_ratio do nome da estatal vs nome do arquivo).
3. Se ainda não bater e existir `caminho_pdf`: extrai texto do PDF com
   `extrair_texto_pdf` (camada nativa por página; OCR quando a página tem pouco texto)
   e aplica de novo os **mesmos** gatilhos de `substrings` ao texto reunido.

Não há mapeamento nome-de-arquivo → estatal no YAML; não há bloco separado de regras
só para o corpo do PDF — os gatilhos de `substrings` servem para nome e para texto.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from rapidfuzz import fuzz

from levantamento_dados_estatais.caminhos_projeto import ARQUIVO_CONFIGURACAO_ESTATAIS_PADRAO

# Outros módulos importam ARQUIVO_CONFIGURACAO_PADRAO
ARQUIVO_CONFIGURACAO_PADRAO = ARQUIVO_CONFIGURACAO_ESTATAIS_PADRAO


def fold_for_match(text: str) -> str:
    """Minúsculas + NFC + remoção aproximada de acentos para comparação estável."""
    nfc = unicodedata.normalize("NFC", text or "")
    nk = unicodedata.normalize("NFKD", nfc)
    stripped = "".join(c for c in nk if unicodedata.category(c) != "Mn")
    return stripped.casefold()


def load_estatais_from_excel(
    excel_path: str | Path,
    *,
    sheet_name: str | int = "Planilha1",
    column: str = "ESTATAL",
) -> list[str]:
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    if column not in df.columns:
        raise KeyError(f"Coluna {column!r} não encontrada. Colunas: {list(df.columns)}")
    series = df[column].dropna().astype(str).str.strip()
    return [x for x in series.tolist() if x]


def _load_yaml_config(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _compile_short_trigger_pattern(trigger_folded: str) -> re.Pattern[str]:
    esc = re.escape(trigger_folded)
    return re.compile(rf"(^|[^a-z0-9]){esc}([^a-z0-9]|$)", re.IGNORECASE)


@dataclass(frozen=True)
class MatchResult:
    estatal: str | None
    metodo: str  # substring | fuzzy | texto_pdf | none


_MAX_PAGINAS_LEITURA_CONTEUDO: int = 12


class EstatalFileMatcher:
    def __init__(
        self,
        estatais: list[str],
        config_path: Path | None = None,
        *,
        fuzzy_min_score: int = 88,
    ) -> None:
        self.estatais = list(estatais)
        self.estatal_set = set(estatais)
        self.fuzzy_min_score = fuzzy_min_score
        path = config_path or ARQUIVO_CONFIGURACAO_ESTATAIS_PADRAO
        raw = _load_yaml_config(path)

        substrings: dict[str, list[str]] = raw.get("substrings") or {}
        self._triggers: list[tuple[str, str, re.Pattern[str] | None]] = []
        for estatal, triggers in substrings.items():
            if estatal not in self.estatal_set:
                raise ValueError(f"Chave em substrings não existe na planilha: {estatal!r}")
            for t in triggers or []:
                t_str = str(t).strip()
                if not t_str:
                    continue
                folded = fold_for_match(t_str)
                pat = (
                    _compile_short_trigger_pattern(folded)
                    if len(folded) <= 4
                    else None
                )
                self._triggers.append((estatal, folded, pat))

        self._triggers.sort(key=lambda x: len(x[1]), reverse=True)

    def _best_substring_estatal(self, folded_haystack: str) -> str | None:
        best_estatal: str | None = None
        best_len = 0
        for estatal, trig, pat in self._triggers:
            if pat is not None:
                if not pat.search(folded_haystack):
                    continue
                hit_len = len(trig)
            else:
                if trig not in folded_haystack:
                    continue
                hit_len = len(trig)
            if hit_len > best_len:
                best_len = hit_len
                best_estatal = estatal
        return best_estatal

    def match_filename(
        self, filename: str, *, caminho_pdf: Path | None = None
    ) -> MatchResult:
        base = os.path.basename(filename)
        folded_name = fold_for_match(base)

        by_name = self._best_substring_estatal(folded_name)
        if by_name is not None:
            return MatchResult(by_name, "substring")

        best_score = 0
        best_fuzzy: str | None = None
        for estatal in self.estatais:
            est_fold = fold_for_match(estatal)
            if len(est_fold) <= 4:
                continue
            sc = fuzz.partial_ratio(est_fold, folded_name)
            if sc > best_score:
                best_score = sc
                best_fuzzy = estatal

        if best_fuzzy is not None and best_score >= self.fuzzy_min_score:
            return MatchResult(best_fuzzy, "fuzzy")

        if caminho_pdf is not None and caminho_pdf.is_file():
            try:
                from levantamento_dados_estatais.pdf_texto import extrair_texto_pdf

                corpo = extrair_texto_pdf(
                    str(caminho_pdf), max_paginas=_MAX_PAGINAS_LEITURA_CONTEUDO
                )
            except Exception:
                corpo = ""
            folded_body = fold_for_match(corpo)
            by_pdf = self._best_substring_estatal(folded_body)
            if by_pdf is not None:
                return MatchResult(by_pdf, "texto_pdf")

        return MatchResult(None, "none")


def scan_folder_pdf_basenames(folder: Path) -> list[str]:
    if not folder.is_dir():
        raise NotADirectoryError(str(folder))
    return sorted(f for f in os.listdir(folder) if f.lower().endswith(".pdf"))
