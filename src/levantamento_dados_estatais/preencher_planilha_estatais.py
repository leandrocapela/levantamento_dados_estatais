#!/usr/bin/env python3
"""
Copia a planilha mestre e preenche células vazias a partir dos PDFs ligados por estatal.

Colunas (só onde vazio):
- QUANTIDADE DE NÍVEIS NA CARREIRA (prioriza PCS)
- TEM ATS? — só SIM com evidência; NÃO só se todos os PDFs tiverem cláusula explícita de ausência;
  caso contrário deixa em branco.
- ANUÊNIO OU QUINQUÊNIO? (prioriza ACT)
- ANO DO PCS (prioriza PCS)
- PREVISÃO DO ATS (PCS OU ACT) — cada frase indica ACT ou PCS e o nome do arquivo.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

from levantamento_dados_estatais.caminhos_projeto import (
    ARQUIVO_CONFIGURACAO_ESTATAIS_PADRAO,
    ARQUIVO_PLANILHA_DADOS_ESTATAIS,
    ARQUIVO_SAIDA_PLANILHA_DADOS_ESTATAIS_PREENCHIDA_AUTOMATICAMENTE,
    PASTA_DOCS_ACORDOS_COLETIVOS_TRABALHO,
    PASTA_DOCS_PLANOS_CARGOS_SALARIOS,
)
from levantamento_dados_estatais.estatal_matching import (
    EstatalFileMatcher,
    load_estatais_from_excel,
    scan_folder_pdf_basenames,
)
from levantamento_dados_estatais.pipeline_extracao import extract_deterministic_compensation_fields

COL_NIVEIS = "QUANTIDADE DE NÍVEIS NA CARREIRA"
COL_TEM_ATS = "TEM ATS?"
COL_TIPO_ATS = "ANUÊNIO OU QUINQUÊNIO?"
COL_ANO_PCS = "ANO DO PCS"
COL_PREVISAO = "PREVISÃO DO ATS (PCS OU ACT)"


def _is_blank(series: pd.Series, idx: int) -> bool:
    v = series.loc[idx]
    if pd.isna(v):
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def _linha_previsao(origem: str, nome_arquivo: str, r: dict) -> str | None:
    """Uma linha com origem ACT|PCS, arquivo e texto útil."""
    if r.get("error"):
        return None
    if r.get("regra_ats") not in (None, "Não encontrado"):
        return f"{origem} ({nome_arquivo}): {r['regra_ats']}"
    if r.get("tipo_ats"):
        return f"{origem} ({nome_arquivo}): tipo ATS: {r['tipo_ats']}"
    if r.get("tem_ats") == "SIM":
        return f"{origem} ({nome_arquivo}): ATS referenciado (sem detalhe de tipo por regex)"
    return None


def _gather_for_estatal(
    caminhos_pdf_acordos_coletivos: list[Path],
    caminhos_pdf_planos_cargos_salarios: list[Path],
    cache: dict[str, dict],
) -> dict[str, object | None]:
    def get_row(p: Path) -> dict:
        k = str(p.resolve())
        if k not in cache:
            cache[k] = extract_deterministic_compensation_fields(k)
        return cache[k]

    niv: int | None = None
    ano: int | None = None
    for p in caminhos_pdf_planos_cargos_salarios:
        r = get_row(p)
        if r.get("error"):
            continue
        if niv is None and r.get("niv_carreira") is not None:
            niv = r["niv_carreira"]
        if ano is None and r.get("ano_pcs") is not None:
            ano = r["ano_pcs"]
    for p in caminhos_pdf_acordos_coletivos:
        r = get_row(p)
        if r.get("error"):
            continue
        if niv is None and r.get("niv_carreira") is not None:
            niv = r["niv_carreira"]
        if ano is None and r.get("ano_pcs") is not None:
            ano = r["ano_pcs"]

    tipo: str | None = None
    for p in caminhos_pdf_acordos_coletivos:
        r = get_row(p)
        if not r.get("error") and r.get("tipo_ats"):
            tipo = r["tipo_ats"]
            break
    if tipo is None:
        for p in caminhos_pdf_planos_cargos_salarios:
            r = get_row(p)
            if not r.get("error") and r.get("tipo_ats"):
                tipo = r["tipo_ats"]
                break

    previsao_lines: list[str] = []
    seen_prev: set[str] = set()
    for label, paths in (
        ("ACT", caminhos_pdf_acordos_coletivos),
        ("PCS", caminhos_pdf_planos_cargos_salarios),
    ):
        for p in paths:
            r = get_row(p)
            ln = _linha_previsao(label, p.name, r)
            if ln and ln not in seen_prev:
                seen_prev.add(ln)
                previsao_lines.append(ln)
    previsao = "\n".join(previsao_lines) if previsao_lines else None

    tem_vals: list[str | None] = []
    for p in list(caminhos_pdf_acordos_coletivos) + list(caminhos_pdf_planos_cargos_salarios):
        r = get_row(p)
        if r.get("error"):
            continue
        tem_vals.append(r.get("tem_ats"))

    tem_ats: str | None = None
    if tem_vals:
        if "SIM" in tem_vals:
            tem_ats = "SIM"
        elif all(v == "NÃO" for v in tem_vals):
            tem_ats = "NÃO"
        else:
            tem_ats = None

    return {
        COL_NIVEIS: niv,
        COL_ANO_PCS: ano,
        COL_TIPO_ATS: tipo,
        COL_TEM_ATS: tem_ats,
        COL_PREVISAO: previsao,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)

    parser = argparse.ArgumentParser(description="Preenche planilha mestre a partir dos PDFs.")
    parser.add_argument("--origem", type=str, default=str(ARQUIVO_PLANILHA_DADOS_ESTATAIS))
    parser.add_argument(
        "--saida",
        type=str,
        default=str(ARQUIVO_SAIDA_PLANILHA_DADOS_ESTATAIS_PREENCHIDA_AUTOMATICAMENTE),
    )
    parser.add_argument("--planilha", type=str, default="Planilha1")
    parser.add_argument(
        "--pasta-docs-acordos-coletivos-trabalho",
        type=str,
        default=str(PASTA_DOCS_ACORDOS_COLETIVOS_TRABALHO),
    )
    parser.add_argument(
        "--pasta-docs-planos-cargos-salarios",
        type=str,
        default=str(PASTA_DOCS_PLANOS_CARGOS_SALARIOS),
    )
    parser.add_argument("--config", type=str, default=str(ARQUIVO_CONFIGURACAO_ESTATAIS_PADRAO))
    args = parser.parse_args()

    origem = Path(args.origem)
    if not origem.is_file():
        print(f"Origem não encontrada: {origem}", file=sys.stderr)
        return 1

    pasta_acordos = Path(args.pasta_docs_acordos_coletivos_trabalho)
    pasta_planos = Path(args.pasta_docs_planos_cargos_salarios)
    cfg = Path(args.config)
    if not cfg.is_file():
        print(f"Config: {cfg} não encontrada", file=sys.stderr)
        return 1

    estatais = load_estatais_from_excel(origem, sheet_name=args.planilha)
    matcher = EstatalFileMatcher(estatais, cfg)

    estatal_para_caminhos_acordos: dict[str, list[Path]] = {}
    estatal_para_caminhos_planos: dict[str, list[Path]] = {}
    for name in scan_folder_pdf_basenames(pasta_acordos):
        m = matcher.match_filename(name)
        if m.estatal:
            estatal_para_caminhos_acordos.setdefault(m.estatal, []).append(pasta_acordos / name)
    for name in scan_folder_pdf_basenames(pasta_planos):
        m = matcher.match_filename(name)
        if m.estatal:
            estatal_para_caminhos_planos.setdefault(m.estatal, []).append(pasta_planos / name)

    df = pd.read_excel(origem, sheet_name=args.planilha)
    fill_cols = [COL_NIVEIS, COL_TEM_ATS, COL_TIPO_ATS, COL_ANO_PCS, COL_PREVISAO]
    for c in fill_cols:
        if c not in df.columns:
            print(f"Coluna em falta: {c!r}", file=sys.stderr)
            return 1
        df[c] = df[c].astype(object)

    cache: dict[str, dict] = {}
    updated_cells = 0

    for idx in df.index:
        est = df.at[idx, "ESTATAL"] if "ESTATAL" in df.columns else None
        if pd.isna(est) or (isinstance(est, str) and not str(est).strip()):
            continue
        est_s = str(est).strip()
        caminhos_acordos = estatal_para_caminhos_acordos.get(est_s, [])
        caminhos_planos = estatal_para_caminhos_planos.get(est_s, [])
        if not caminhos_acordos and not caminhos_planos:
            continue

        merged = _gather_for_estatal(caminhos_acordos, caminhos_planos, cache)
        for col, val in merged.items():
            if val is None:
                continue
            if not _is_blank(df[col], idx):
                continue
            df.at[idx, col] = val
            updated_cells += 1

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=args.planilha, index=False)

    print(f"Escrito: {saida.resolve()}")
    print(f"PDFs únicos: {len(cache)} | células preenchidas: {updated_cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
