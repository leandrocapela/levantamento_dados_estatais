"""
Relaciona nomes de arquivos PDF (ACT / PCS) à coluna ESTATAL de Dados Estatais.xlsx.

Ordem de decisão:
1. Mapeamento explícito por nome de arquivo (config YAML).
2. Maior substring configurada (com regra especial para gatilhos curtos).
3. Fuzzy partial ratio (rapidfuzz) acima de um limiar, só se ainda não houver match.
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
    metodo: str  # explicit | substring | fuzzy | none


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

        arquivo_para = raw.get("arquivo_para_estatal") or {}
        self._explicit_folded: dict[str, str] = {}
        for nome_arquivo, estatal in arquivo_para.items():
            if estatal not in self.estatal_set:
                raise ValueError(
                    f"ESTATAL desconhecida em arquivo_para_estatal: {estatal!r} "
                    f"(arquivo {nome_arquivo!r})"
                )
            self._explicit_folded[fold_for_match(str(nome_arquivo))] = estatal

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

    def match_filename(self, filename: str) -> MatchResult:
        base = os.path.basename(filename)
        folded_name = fold_for_match(base)

        if folded_name in self._explicit_folded:
            e = self._explicit_folded[folded_name]
            return MatchResult(e, "explicit")

        best_estatal: str | None = None
        best_len = 0
        for estatal, trig, pat in self._triggers:
            if pat is not None:
                if not pat.search(folded_name):
                    continue
                hit_len = len(trig)
            else:
                if trig not in folded_name:
                    continue
                hit_len = len(trig)
            if hit_len > best_len:
                best_len = hit_len
                best_estatal = estatal

        if best_estatal is not None:
            return MatchResult(best_estatal, "substring")

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

        return MatchResult(None, "none")


def scan_folder_pdf_basenames(folder: Path) -> list[str]:
    if not folder.is_dir():
        raise NotADirectoryError(str(folder))
    return sorted(f for f in os.listdir(folder) if f.lower().endswith(".pdf"))
