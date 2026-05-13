#!/usr/bin/env python3
"""
Copia a planilha mestre e preenche células a partir dos PDFs ligados por estatal.

Colunas sempre atualizadas a partir do match nome/texto do PDF:
- ACT — **um** nome de PDF de ACT (representativo: prioridade substring, depois fuzzy, depois
  texto no PDF; empate pelo nome do arquivo). A extração de campos continua a considerar
  **todos** os PDFs que casaram com a estatal.
- PCS — idem para PCS.

Colunas (só onde vazio), além de ACT/PCS:
- QUANTIDADE DE NÍVEIS NA CARREIRA (prioriza PCS)
- TEM ATS? — só SIM com evidência; NÃO só se todos os PDFs tiverem cláusula explícita de ausência;
  caso contrário deixa em branco.
- ANUÊNIO OU QUINQUÊNIO? (prioriza ACT)
- ANO DO PCS (prioriza PCS)
- PREVISÃO DO ATS (PCS OU ACT) — ATS clássico e **blocos dos três pilares** (salário base, ATS com %/teto, gratificações) por arquivo.
- PERCENTUAL — se a coluna existir na planilha, preenche com o **primeiro** percentual de ATS inferido pelos regex (PCS depois ACT).
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

COL_ACT = "ACT"
COL_PCS = "PCS"
COL_NIVEIS = "QUANTIDADE DE NÍVEIS NA CARREIRA"
COL_TEM_ATS = "TEM ATS?"
COL_TIPO_ATS = "ANUÊNIO OU QUINQUÊNIO?"
COL_ANO_PCS = "ANO DO PCS"
COL_PREVISAO = "PREVISÃO DO ATS (PCS OU ACT)"
COL_PERCENTUAL = "PERCENTUAL"

# Ordem para escolher um único arquivo nas colunas ACT / PCS (vários PDFs podem casar).
_METODO_RANK: dict[str, int] = {"substring": 3, "fuzzy": 2, "texto_pdf": 1, "none": 0}


def _caminhos_unicos_ordenados(scored: list[tuple[int, Path]]) -> list[Path]:
    """Preserva ordem de entrada, remove duplicados por caminho."""
    seen: set[str] = set()
    out: list[Path] = []
    for _, p in scored:
        k = str(p.resolve())
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def _nome_arquivo_representativo(scored: list[tuple[int, Path]]) -> str:
    """Um basename: maior rank de match; empate → nome de arquivo lexicograficamente menor."""
    if not scored:
        return ""
    best = max(r for r, _ in scored)
    cands = [p for r, p in scored if r == best]
    return sorted(cands, key=lambda p: p.name)[0].name


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


def _linhas_pilares_remuneracao(origem: str, nome_arquivo: str, r: dict) -> list[str]:
    """Evidências dos três pilares: salário base, ATS (%/teto), gratificações."""
    if r.get("error"):
        return []
    out: list[str] = []
    if r.get("salario_grade_resumo"):
        out.append(f"{origem} ({nome_arquivo}) [Salário base]: {r['salario_grade_resumo']}")
    bits: list[str] = []
    if r.get("ats_percentual"):
        bits.append(f"≈{r['ats_percentual']}%")
    if r.get("ats_teto_resumo"):
        bits.append(r["ats_teto_resumo"][:240])
    if bits:
        out.append(f"{origem} ({nome_arquivo}) [ATS]: " + " — ".join(bits))
    if r.get("gratificacoes_resumo"):
        out.append(f"{origem} ({nome_arquivo}) [Gratificações]: {r['gratificacoes_resumo'][:700]}")
    return out


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
            for pl in _linhas_pilares_remuneracao(label, p.name, r):
                if pl not in seen_prev:
                    seen_prev.add(pl)
                    previsao_lines.append(pl)
    previsao = "\n".join(previsao_lines) if previsao_lines else None

    percentual_ats: str | None = None
    for lista in (caminhos_pdf_planos_cargos_salarios, caminhos_pdf_acordos_coletivos):
        for p in lista:
            r = get_row(p)
            if r.get("error"):
                continue
            ap = r.get("ats_percentual")
            if ap and percentual_ats is None:
                percentual_ats = str(ap).replace(".", ",")

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
        COL_PERCENTUAL: percentual_ats,
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

    estatal_para_scored_acordos: dict[str, list[tuple[int, Path]]] = {}
    estatal_para_scored_planos: dict[str, list[tuple[int, Path]]] = {}
    for name in scan_folder_pdf_basenames(pasta_acordos):
        m = matcher.match_filename(name, caminho_pdf=pasta_acordos / name)
        if m.estatal:
            rk = _METODO_RANK.get(m.metodo, 0)
            estatal_para_scored_acordos.setdefault(m.estatal, []).append(
                (rk, pasta_acordos / name)
            )
    for name in scan_folder_pdf_basenames(pasta_planos):
        m = matcher.match_filename(name, caminho_pdf=pasta_planos / name)
        if m.estatal:
            rk = _METODO_RANK.get(m.metodo, 0)
            estatal_para_scored_planos.setdefault(m.estatal, []).append(
                (rk, pasta_planos / name)
            )

    df = pd.read_excel(origem, sheet_name=args.planilha)
    if "ESTATAL" not in df.columns:
        print("Coluna ESTATAL em falta na planilha.", file=sys.stderr)
        return 1

    if COL_ACT not in df.columns:
        pos = int(df.columns.get_loc("ESTATAL")) + 1
        df.insert(pos, COL_ACT, pd.NA)
        df.insert(pos + 1, COL_PCS, pd.NA)
    else:
        if COL_PCS not in df.columns:
            pos = int(df.columns.get_loc(COL_ACT)) + 1
            df.insert(pos, COL_PCS, pd.NA)
        df[COL_ACT] = df[COL_ACT].astype(object)
        df[COL_PCS] = df[COL_PCS].astype(object)

    fill_cols = [COL_NIVEIS, COL_TEM_ATS, COL_TIPO_ATS, COL_ANO_PCS, COL_PREVISAO]
    if COL_PERCENTUAL in df.columns:
        fill_cols.append(COL_PERCENTUAL)
    for c in fill_cols:
        if c not in df.columns:
            print(f"Coluna em falta: {c!r}", file=sys.stderr)
            return 1
        df[c] = df[c].astype(object)

    cache: dict[str, dict] = {}
    updated_cells = 0

    for idx in df.index:
        est = df.at[idx, "ESTATAL"]
        if pd.isna(est) or (isinstance(est, str) and not str(est).strip()):
            continue
        est_s = str(est).strip()
        scored_ac = estatal_para_scored_acordos.get(est_s, [])
        scored_pc = estatal_para_scored_planos.get(est_s, [])
        caminhos_acordos = _caminhos_unicos_ordenados(scored_ac)
        caminhos_planos = _caminhos_unicos_ordenados(scored_pc)

        act_cell = _nome_arquivo_representativo(scored_ac)
        pcs_cell = _nome_arquivo_representativo(scored_pc)
        df.at[idx, COL_ACT] = act_cell if act_cell else pd.NA
        df.at[idx, COL_PCS] = pcs_cell if pcs_cell else pd.NA

        if not caminhos_acordos and not caminhos_planos:
            continue

        merged = _gather_for_estatal(caminhos_acordos, caminhos_planos, cache)
        for col, val in merged.items():
            if col not in df.columns:
                continue
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
