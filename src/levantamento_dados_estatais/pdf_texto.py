"""
Extração de texto de PDF: camada nativa (PyMuPDF) e OCR (Tesseract) por página.

O OCR só roda nas primeiras páginas do intervalo pedido e só quando o texto nativo
da página é curto — típico de PDF escaneado. Desative com a variável de ambiente
LEV_DADOS_PDF_OCR=0. É necessário o binário `tesseract` (ex.: brew install tesseract
tesseract-lang no macOS). Se não estiver no PATH do Cursor, defina LEV_DADOS_TESSERACT_CMD
com o caminho completo (ex.: /opt/homebrew/bin/tesseract).
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import unicodedata

import fitz

logger = logging.getLogger(__name__)

# Página com menos caracteres que isso tenta OCR (se Tesseract disponível).
_MINIMO_CARACTERES_TEXTO_NATIVO: int = 45
# Limite de páginas (a partir do início do intervalo) onde o OCR pode ser aplicado.
_MAXIMO_PAGINAS_COM_OCR: int = 25

_tesseract_ok: bool | None = None
_tesseract_cmd_configurado: str | None = None
_ocr_cache_env: str | None = None


def _caminhos_candidatos_tesseract() -> list[str]:
    """Ordem: variáveis de ambiente, PATH, locais típicos do Homebrew no macOS."""
    vistos: set[str] = set()
    saida: list[str] = []
    for var in ("LEV_DADOS_TESSERACT_CMD", "TESSERACT_CMD"):
        raw = (os.environ.get(var) or "").strip()
        if raw and raw not in vistos:
            vistos.add(raw)
            saida.append(raw)
    which = shutil.which("tesseract")
    if which and which not in vistos:
        vistos.add(which)
        saida.append(which)
    if sys.platform == "darwin":
        for fixo in ("/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"):
            if fixo not in vistos:
                vistos.add(fixo)
                saida.append(fixo)
    return saida


def _resolver_e_configurar_tesseract() -> str | None:
    """Define `pytesseract.pytesseract.tesseract_cmd` e devolve o caminho usado, ou None."""
    global _tesseract_cmd_configurado
    import pytesseract

    for candidato in _caminhos_candidatos_tesseract():
        if not candidato:
            continue
        if not os.path.isfile(candidato):
            continue
        if sys.platform != "win32" and not os.access(candidato, os.X_OK):
            continue
        pytesseract.pytesseract.tesseract_cmd = candidato
        _tesseract_cmd_configurado = candidato
        return candidato
    return None


def _ocr_desativado_por_ambiente() -> bool:
    v = os.environ.get("LEV_DADOS_PDF_OCR", "1").strip().lower()
    return v in ("0", "false", "no", "off")


def _tesseract_disponivel() -> bool:
    global _tesseract_ok, _ocr_cache_env
    if _ocr_desativado_por_ambiente():
        return False
    env_snap = f"{os.environ.get('LEV_DADOS_TESSERACT_CMD', '')}|{os.environ.get('TESSERACT_CMD', '')}"
    if env_snap != _ocr_cache_env:
        _ocr_cache_env = env_snap
        _tesseract_ok = None
    if _tesseract_ok is not None:
        return _tesseract_ok
    try:
        import pytesseract

        cmd = _resolver_e_configurar_tesseract()
        if cmd is None:
            logger.warning(
                "OCR (Tesseract): binário não encontrado. Instale (ex.: brew install "
                "tesseract tesseract-lang) ou defina LEV_DADOS_TESSERACT_CMD com o caminho "
                "completo do executável (ex.: /opt/homebrew/bin/tesseract)."
            )
            _tesseract_ok = False
            return False
        pytesseract.get_tesseract_version()
        _tesseract_ok = True
        logger.info("OCR Tesseract ativo: %s", cmd)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR (Tesseract) indisponível: %s", exc)
        _tesseract_ok = False
    return bool(_tesseract_ok)


def _ocr_em_pagina(page: fitz.Page) -> str:
    import pytesseract
    from PIL import Image

    # Zoom 2x melhora leitura em scans de baixa resolução.
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    modo = "RGB" if pix.n == 3 else "RGBA"
    img = Image.frombytes(modo, [pix.width, pix.height], pix.samples)
    if img.mode != "RGB":
        img = img.convert("RGB")
    # por+eng: siglas e cabeçalhos bilíngues; fallback se pacote de idioma não estiver instalado.
    for idioma in ("por+eng", "por", "eng"):
        try:
            texto = pytesseract.image_to_string(
                img, lang=idioma, config="--oem 3 --psm 6"
            )
            return unicodedata.normalize("NFC", texto or "")
        except Exception:  # noqa: BLE001 — TesseractError conforme versão
            continue
    return ""


def extrair_texto_pdf(
    caminho_arquivo: str,
    max_paginas: int | None = None,
) -> str:
    """
    Junta o texto das primeiras `max_paginas` páginas (ou do documento inteiro se None).
    Em páginas com pouco texto nativo, tenta OCR nas primeiras `_MAXIMO_PAGINAS_COM_OCR`
    páginas do recorte.
    """
    doc = fitz.open(caminho_arquivo)
    try:
        total = len(doc)
        n = total if max_paginas is None else min(total, max_paginas)
        usar_ocr = _tesseract_disponivel()
        partes: list[str] = []
        for indice in range(n):
            pagina = doc[indice]
            nativo = pagina.get_text() or ""
            if len(nativo.strip()) >= _MINIMO_CARACTERES_TEXTO_NATIVO or not usar_ocr:
                partes.append(nativo)
            elif indice < _MAXIMO_PAGINAS_COM_OCR:
                try:
                    partes.append(_ocr_em_pagina(pagina))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Falha ao OCR da página %s em %s: %s", indice, caminho_arquivo, exc
                    )
                    partes.append(nativo)
            else:
                partes.append(nativo)
        return unicodedata.normalize("NFC", "".join(partes))
    finally:
        doc.close()
