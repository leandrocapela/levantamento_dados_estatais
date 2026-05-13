#!/usr/bin/env python3
"""CLI: testa extração nativa + OCR num único PDF (diagnóstico)."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import fitz


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mostra texto nativo vs extrair_texto_pdf (com OCR se Tesseract existir)."
    )
    parser.add_argument("pdf", type=Path, help="Caminho para o .pdf")
    parser.add_argument(
        "--paginas",
        type=int,
        default=3,
        metavar="N",
        help="Máximo de páginas a ler (por padrão 3)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        print(f"Arquivo não encontrado: {pdf}", file=sys.stderr)
        return 1

    # Limpa cache do detector (útil em REPL / várias execuções)
    import levantamento_dados_estatais.pdf_texto as pt

    pt._tesseract_ok = None
    pt._ocr_cache_env = None

    from levantamento_dados_estatais.pdf_texto import _tesseract_disponivel, extrair_texto_pdf

    print("Arquivo:", pdf)
    print("Tesseract disponível:", _tesseract_disponivel())
    try:
        import pytesseract

        print("tesseract_cmd:", getattr(pytesseract.pytesseract, "tesseract_cmd", "(padrão)"))
    except ImportError:
        print("pytesseract não instalado (pip install pytesseract Pillow)")

    doc = fitz.open(pdf)
    try:
        n = min(len(doc), max(1, args.paginas))
        for i in range(n):
            nat = (doc[i].get_text() or "").strip()
            print(f"\n--- Página {i + 1} | nativo PyMuPDF | len={len(nat)} ---")
            print(repr(nat[:400]))
    finally:
        doc.close()

    print(f"\n=== extrair_texto_pdf (max_paginas={args.paginas}) ===")
    texto = extrair_texto_pdf(str(pdf), max_paginas=args.paginas)
    print("len total:", len(texto))
    if texto.strip():
        print("--- amostra (1200 chars) ---")
        print(texto[:1200])
    else:
        print("(vazio — sem texto nativo e OCR inativo ou falhou em todas as páginas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
