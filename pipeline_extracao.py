
import pandas as pd
import fitz
import os

def get_pdf_text(file_path, max_pages=10):
    """
    Extrai texto bruto do PDF para processamento.
    """
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc[:max_pages]:
            text += page.get_text()
        return text
    except Exception as e:
        return f"Erro ao ler PDF: {str(e)}"

def list_files_summary(folder_path):
    if not os.path.exists(folder_path):
        return []
    return os.listdir(folder_path)
