# 📊 Pipeline de Extração de Dados: Estatais Brasileiras

Este repositório contém a inteligência e a automação para a coleta determinística de dados de remuneração e benefícios de empresas estatais federais, focando em **Acordos Coletivos de Trabalho (ACT)** e **Planos de Cargos e Salários (PCS)**.

## 🎯 Objetivo do Projeto
O objetivo é transformar documentos não estruturados (PDFs complexos) em uma base de dados estruturada para análise comparativa de mercado, utilizando Processamento de Linguagem Natural (NLP) e Visão Computacional.

## 🛠️ Stack Tecnológica
- **Linguagem:** Python 3.12
- **IA Generativa:** Google Gemini 2.0 Flash (via Google AI SDK)
- **Processamento de PDF:** PyMuPDF (fitz) para extração de texto e análise de tabelas.
- **Manipulação de Dados:** Pandas & OpenPyXL.
- **Infraestrutura:** Google Colab integrado ao Google Drive.

## 📂 Estrutura de Dados
O pipeline processa arquivos organizados em:
- `ACTs/`: Acordos vigentes que definem reajustes e cláusulas sociais.
- `Planos de Cargos e Salários/`: Tabelas salariais, steps de carreira e regras de promoção.
- `Dados Estatais.xlsx`: O output consolidado de todo o processamento.

## ⚙️ Fluxo de Trabalho (Pipeline)
1. **Sincronização:** Arquivos são espelhados do Google Drive para o ambiente de execução.
2. **Extração:** O PyMuPDF isola as seções relevantes (primeiras páginas e tabelas).
3. **Inteligência:** O Gemini 2.0 analisa o contexto e extrai: 
    - Vencimento Básico (Min/Max)
    - Periodicidade (Mensal/Horista)
    - Regras de ATS (Anuênio/Quinquênio)
4. **Consolidação:** Os dados são validados e salvos na planilha mestre.

---
*Desenvolvido para o GT de Cargos e Salários.*
