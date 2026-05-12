
import pandas as pd
import fitz
import os
import re
import json

def extract_deterministic_data(file_path):
    """
    Extrai dados usando padrões de Regex (Regex-based extraction).
    """
    try:
        doc = fitz.open(file_path)
        text = "".join([page.get_text() for page in doc[:15]])

        # Exemplo de padrões Regex para Vencimento e ATS
        patterns = {
            'vencimento_min': r'(?:Vencimento|Salário)\s*(?:Básico|Mínimo)\D*([\d.,]+)',
            'periodicidade': r'(Mensal|Horista|Por hora)',
            'regra_ats': r'(Anuênio|Quinquenio|Adicional por Tempo de Serviço)'
        }

        results = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            results[key] = match.group(1) if match else "Não encontrado"

        return results
    except Exception as e:
        return {"error": str(e)}

def run_pipeline(input_folder, output_excel):
    if not os.path.exists(input_folder):
        print(f"Erro: Pasta {input_folder} não encontrada.")
        return
    
    files = [f for f in os.listdir(input_folder) if f.endswith('.pdf')]
    all_data = []

    for f in files:
        print(f"-> Analisando via Regex: {f}")
        data = extract_deterministic_data(os.path.join(input_folder, f))
        data['arquivo'] = f
        all_data.append(data)

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_excel(output_excel, index=False)
        print(f"\n✅ Processamento Regex finalizado: {output_excel}")
    else:
        print("Nenhum arquivo PDF encontrado para processar.")

if __name__ == '__main__':
    # Para rodar via terminal: python pipeline_extracao.py
    pass
