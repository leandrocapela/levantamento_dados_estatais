#!/usr/bin/env python3
"""CLI: extrai JSON niv_carreira / tem_ats / tipo_ats / ano_pcs de PDFs."""
from __future__ import annotations

import argparse
import json
import os
import sys

from levantamento_dados_estatais.pipeline_extracao import extract_act_pcs_schema_from_pdf


def main() -> int:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    os.chdir(root)

    parser = argparse.ArgumentParser(
        description="Extrai niv_carreira, tem_ats, tipo_ats, ano_pcs de PDFs ACT/PCS."
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--pdf", type=str, help="Caminho para um único PDF")
    g.add_argument("--pasta", type=str, help="Pasta contendo PDFs")
    parser.add_argument("--max-paginas", type=int, default=None, metavar="N")
    parser.add_argument("--saida", type=str, default="")
    args = parser.parse_args()

    if args.pdf:
        path = args.pdf if os.path.isabs(args.pdf) else os.path.join(root, args.pdf)
        if not os.path.isfile(path):
            print(f"Arquivo não encontrado: {path}", file=sys.stderr)
            return 1
        record = extract_act_pcs_schema_from_pdf(path, max_pages=args.max_paginas)
        record = {**record, "arquivo": os.path.basename(path)}
        payload = record
    else:
        folder = args.pasta if os.path.isabs(args.pasta) else os.path.join(root, args.pasta)
        if not os.path.isdir(folder):
            print(f"Pasta não encontrada: {folder}", file=sys.stderr)
            return 1
        records: list[dict] = []
        for name in sorted(f for f in os.listdir(folder) if f.lower().endswith(".pdf")):
            fp = os.path.join(folder, name)
            row = extract_act_pcs_schema_from_pdf(fp, max_pages=args.max_paginas)
            row["arquivo"] = name
            records.append(row)
        payload = records

    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.saida:
        out_path = args.saida if os.path.isabs(args.saida) else os.path.join(root, args.saida)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)
        print(out_path)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
