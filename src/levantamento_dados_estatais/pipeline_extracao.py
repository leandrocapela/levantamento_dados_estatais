import os
import re
import unicodedata

import fitz
import pandas as pd


def _normalize_to_nfc(text: str) -> str:
    """Return Unicode NFC-normalized text for stable regex over PDF extractions."""
    return unicodedata.normalize("NFC", text or "")


def extract_plain_text_from_pdf(file_path: str, max_pages: int | None = None) -> str:
    """
    Concatenate plain text from PDF pages using PyMuPDF.
    If max_pages is None, reads the entire document; otherwise caps at N first pages.
    """
    doc = fitz.open(file_path)
    n = len(doc) if max_pages is None else min(len(doc), max_pages)
    parts = [doc[i].get_text() for i in range(n)]
    doc.close()
    return _normalize_to_nfc("".join(parts))


def _regex_match_start_index(pattern: str, haystack: str) -> int | None:
    match = re.search(pattern, haystack, re.I)
    return match.start() if match else None


# "NÃO" a ATS só com menção explícita de inexistência/supressão (ausência de palavra-chave não basta).
_EXPLICIT_NO_ATS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.I)
    for p in (
        r"n[aã]o\s+h[áa]\s+(?:anu[eê]nio|quinqu[eê]nio|adicional\s+por\s+tempo\s+de\s+servi[cç]o|\bats\b)",
        r"(?:anu[eê]nio|quinqu[eê]nio|\bats\b)\s+n[aã]o\s+(?:ser[aá]\s+)?(?:pago|paga|concedido|concedida|devido|devida|aplic[aá]vel)",
        r"(?:anu[eê]nio|quinqu[eê]nio|\bats\b)\s+(?:suprimido|extinto|revogado|revogada)",
        r"vedad[oa]\s+.{0,40}(?:anu[eê]nio|quinqu[eê]nio|adicional\s+por\s+tempo|\bats\b)",
        r"inexist[eê]ncia\s+de\s+.{0,30}(?:anu[eê]nio|quinqu[eê]nio|adicional\s+por\s+tempo|\bats\b)",
    )
)


def _has_explicit_no_ats(lower_text: str) -> bool:
    return any(p.search(lower_text) for p in _EXPLICIT_NO_ATS_PATTERNS)


def build_act_pcs_schema_from_extracted_text(extracted_text: str, file_path_for_metadata: str) -> dict:
    """
    Build the deterministic ACT/PCS schema dict from already-extracted PDF text.
    file_path_for_metadata is used for year hints from the filename when needed.

    tem_ats: "SIM" com evidência positiva; "NÃO" só com cláusula explícita de inexistência/supressão;
             caso contrário None (indeterminado — não inferir ausência por silêncio).
    """
    normalized = _normalize_to_nfc(extracted_text)
    lower = normalized.lower()

    ano_pcs = None
    base = os.path.basename(file_path_for_metadata)
    year_in_name = re.search(r"(20[12]\d)", base)
    if year_in_name:
        ano_pcs = int(year_in_name.group(1))
    else:
        vig_match = re.search(
            r"(?:vig[eê]ncia|per[ií]odo|refer[eê]ncia)\D{0,40}(20[12]\d)",
            lower,
            re.I,
        )
        if vig_match:
            ano_pcs = int(vig_match.group(1))

    has_anuenio = bool(re.search(r"anu[eê]nio", lower))
    has_quinquenio = bool(re.search(r"quinqu[eê]nio", lower))
    has_generic_ats = bool(
        re.search(r"adicional\s+por\s+tempo\s+de\s+servi[cç]o", lower)
        or re.search(r"\bats\b", lower)
    )

    has_positive = has_anuenio or has_quinquenio or has_generic_ats
    if has_positive:
        tem_ats: str | None = "SIM"
    elif _has_explicit_no_ats(lower):
        tem_ats = "NÃO"
    else:
        tem_ats = None

    tipo_ats = None
    if has_quinquenio and not has_anuenio:
        tipo_ats = "QUINQUÊNIO"
    elif has_anuenio and not has_quinquenio:
        tipo_ats = "ANUÊNIO"
    elif has_quinquenio and has_anuenio:
        anuenio_pos = _regex_match_start_index(r"anu[eê]nio", lower)
        quinquenio_pos = _regex_match_start_index(r"quinqu[eê]nio", lower)
        if anuenio_pos is not None and quinquenio_pos is not None:
            tipo_ats = "ANUÊNIO" if anuenio_pos <= quinquenio_pos else "QUINQUÊNIO"
        elif anuenio_pos is not None:
            tipo_ats = "ANUÊNIO"
        else:
            tipo_ats = "QUINQUÊNIO"

    niv_carreira = None
    career_level_patterns = [
        r"(?:total\s+de|s[aã]o|composto\s+de|composta\s+de)\s+(\d{1,2})\s+n[ií]veis?",
        r"(\d{1,2})\s+n[ií]veis?\s+(?:salariais|da\s+carreira|de\s+vencimento)",
        r"(\d{1,2})\s+faixas?\s+(?:salariais|salarial|de\s+vencimento|remunerat[oó]rias?)",
        r"(\d{1,2})\s+degraus?",
        r"grau\s*(\d{1,2})\s*(?:a|at[eé])\s*grau\s*(\d{1,2})",
    ]
    for pat in career_level_patterns:
        match = re.search(pat, lower, re.I)
        if not match:
            continue
        if len(match.groups()) == 2:
            low_grau, high_grau = int(match.group(1)), int(match.group(2))
            niv_carreira = max(low_grau, high_grau) - min(low_grau, high_grau) + 1
        else:
            niv_carreira = int(match.group(1))
        if 1 <= niv_carreira <= 50:
            break
        niv_carreira = None

    return {
        "niv_carreira": niv_carreira,
        "tem_ats": tem_ats,
        "tipo_ats": tipo_ats,
        "ano_pcs": ano_pcs,
    }


def extract_act_pcs_schema_from_pdf(file_path: str, max_pages: int | None = None) -> dict:
    text = extract_plain_text_from_pdf(file_path, max_pages=max_pages)
    return build_act_pcs_schema_from_extracted_text(text, file_path)


def extract_deterministic_compensation_fields(file_path: str, max_pages: int | None = None) -> dict:
    try:
        text = extract_plain_text_from_pdf(file_path, max_pages=max_pages)

        legacy_patterns = {
            "vencimento_min": r"(?:Vencimento|Sal[aá]rio)\s*(?:B[aá]sico|M[ií]nimo)\D*([\d.,]+)",
            "periodicidade": r"(Mensal|Horista|Por hora)",
            "regra_ats": r"(Anu[eê]nio|Quinqu[eê]nio|Adicional por Tempo de Servi[cç]o)",
        }

        row: dict = {}
        for key, pattern in legacy_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            row[key] = match.group(1) if match else "Não encontrado"

        act_pcs_schema = build_act_pcs_schema_from_extracted_text(text, file_path)
        row.update(
            {
                "niv_carreira": act_pcs_schema["niv_carreira"],
                "tem_ats": act_pcs_schema["tem_ats"],
                "tipo_ats": act_pcs_schema["tipo_ats"],
                "ano_pcs": act_pcs_schema["ano_pcs"],
            }
        )
        return row
    except Exception as exc:
        return {"error": str(exc)}


def export_pdf_folder_to_excel(pdf_folder_path: str, output_excel_path: str) -> None:
    if not os.path.exists(pdf_folder_path):
        print(f"Erro: Pasta {pdf_folder_path} não encontrada.")
        return

    pdf_names = [f for f in os.listdir(pdf_folder_path) if f.lower().endswith(".pdf")]
    all_rows: list[dict] = []

    for name in sorted(pdf_names):
        print(f"-> Analisando via Regex: {name}")
        file_path = os.path.join(pdf_folder_path, name)
        row = extract_deterministic_compensation_fields(file_path)
        row["arquivo"] = name
        all_rows.append(row)

    if all_rows:
        df = pd.DataFrame(all_rows)
        os.makedirs(os.path.dirname(output_excel_path) or ".", exist_ok=True)
        df.to_excel(output_excel_path, index=False)
        print(f"\n✅ Processamento Regex finalizado: {output_excel_path}")
    else:
        print("Nenhum arquivo PDF encontrado para processar.")


def main(argv: list[str] | None = None) -> int:
    import argparse

    from levantamento_dados_estatais.caminhos_projeto import (
        ARQUIVO_SAIDA_EXTRACAO_PIPELINE_REGEX,
        DIRETORIO_OUTPUT,
        PASTA_DOCUMENTOS_ACORDOS_COLETIVOS_TRABALHO,
    )

    parser = argparse.ArgumentParser(description="Pipeline de extração determinística (ACT/PCS).")
    parser.add_argument(
        "--pasta",
        type=str,
        default=str(PASTA_DOCUMENTOS_ACORDOS_COLETIVOS_TRABALHO),
        help="Pasta com PDFs",
    )
    parser.add_argument(
        "--saida",
        type=str,
        default=str(ARQUIVO_SAIDA_EXTRACAO_PIPELINE_REGEX),
        help="Planilha de saída",
    )
    args = parser.parse_args(argv)
    os.makedirs(DIRETORIO_OUTPUT, exist_ok=True)
    export_pdf_folder_to_excel(args.pasta, args.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
