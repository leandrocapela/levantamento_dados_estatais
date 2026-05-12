
import pandas as pd
import fitz
import json
import google.generativeai as genai

def extract_pdf_data(file_path, model):
    try:
        doc = fitz.open(file_path)
        text = "".join([page.get_text() for page in doc[:10]])
        prompt = f"Analise o texto e extraia em JSON: vencimento_min, vencimento_max, periodicidade, regra_ats. Texto: {text[:10000]}"
        response = model.generate_content(prompt)
        return json.loads(response.text.strip())
    except Exception as e:
        return {"error": str(e)}
