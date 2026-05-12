#!/usr/bin/env python3
"""CLI: relaciona PDFs em pastas de actos/planos à coluna ESTATAL."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

from levantamento_dados_estatais.caminhos_projeto import (
    ARQUIVO_PLANILHA_DADOS_ESTATAIS,
    ARQUIVO_SAIDA_MAPEAMENTO_ARQUIVOS_ESTATAIS,
    PASTA_DOCUMENTOS_ACORDOS_COLETIVOS_TRABALHO,
    PASTA_DOCUMENTOS_PLANOS_CARGOS_SALARIOS,
)
from levantamento_dados_estatais.estatal_matching import (
    EstatalFileMatcher,
    ARQUIVO_CONFIGURACAO_PADRAO,
    load_estatais_from_excel,
    scan_folder_pdf_basenames,
)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)

    parser = argparse.ArgumentParser(
        description="Relaciona PDFs de ACT/PCS à coluna ESTATAL de Dados Estatais.xlsx."
    )
    parser.add_argument(
        "--planilha",
        type=str,
        default=str(ARQUIVO_PLANILHA_DADOS_ESTATAIS),
        help="Caminho para Dados Estatais.xlsx",
    )
    parser.add_argument(
        "--pasta-documentos-acordos-coletivos-trabalho",
        type=str,
        default=str(PASTA_DOCUMENTOS_ACORDOS_COLETIVOS_TRABALHO),
        help="Pasta com PDFs de acordos coletivos de trabalho",
    )
    parser.add_argument(
        "--pasta-documentos-planos-cargos-salarios",
        type=str,
        default=str(PASTA_DOCUMENTOS_PLANOS_CARGOS_SALARIOS),
        help="Pasta com PDFs de planos de cargos e salários",
    )
    parser.add_argument("--config", type=str, default=str(ARQUIVO_CONFIGURACAO_PADRAO))
    parser.add_argument(
        "--saida",
        type=str,
        default=str(ARQUIVO_SAIDA_MAPEAMENTO_ARQUIVOS_ESTATAIS),
    )
    parser.add_argument("--fuzzy-min", type=int, default=88)
    args = parser.parse_args()

    excel = Path(args.planilha)
    if not excel.is_file():
        print(f"Planilha não encontrada: {excel.resolve()}", file=sys.stderr)
        return 1

    pasta_acordos = Path(args.pasta_documentos_acordos_coletivos_trabalho)
    pasta_planos = Path(args.pasta_documentos_planos_cargos_salarios)
    for d, label in ((pasta_acordos, "acordos"), (pasta_planos, "planos")):
        if not d.is_dir():
            print(f"Pasta {label} não encontrada: {d.resolve()}", file=sys.stderr)
            return 1

    cfg = Path(args.config)
    if not cfg.is_file():
        print(f"Config não encontrada: {cfg.resolve()}", file=sys.stderr)
        return 1

    estatais = load_estatais_from_excel(excel)
    matcher = EstatalFileMatcher(estatais, cfg, fuzzy_min_score=args.fuzzy_min)

    rows: list[dict[str, object]] = []
    for label, folder in (("ACT", pasta_acordos), ("PCS", pasta_planos)):
        for name in scan_folder_pdf_basenames(folder):
            res = matcher.match_filename(name)
            rows.append(
                {
                    "tipo": label,
                    "pasta": folder.name,
                    "arquivo": name,
                    "estatal": res.estatal,
                    "metodo_match": res.metodo,
                }
            )

    df = pd.DataFrame(rows)
    arquivo_saida = Path(args.saida)
    arquivo_saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(arquivo_saida, index=False)

    sem = df["estatal"].isna()
    n_sem = int(sem.sum())
    print(f"Escrito: {arquivo_saida.resolve()} ({len(df)} linhas, {n_sem} sem estatal)")
    if n_sem:
        print("Arquivos sem match:")
        for a in df.loc[sem, "arquivo"].tolist():
            print(f"  - {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
