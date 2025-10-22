# Lotofácil Analyzer 🎲

Aplicação em Python com interface web (Streamlit) para analisar resultados da Lotofácil e gerar novas combinações inteligentes.

## Funcionalidades
- Upload de planilha (Excel ou CSV) com resultados históricos
- Análise do último sorteio vs. anteriores (5 a 14 acertos)
- Estatísticas de pares, ímpares e soma
- Geração de novas combinações com filtros de paridade
- Exportação automática em Excel

## Como executar localmente
```bash
pip install -r requirements.txt
streamlit run lotofacil_analyzer_app.py
