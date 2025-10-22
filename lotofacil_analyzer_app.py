# lotofacil_analyzer_app.py
import streamlit as st
import pandas as pd
import numpy as np
from itertools import combinations
import random
from datetime import datetime
import io

st.set_page_config(page_title="Lotofácil Analyzer", layout="wide")

st.title("Lotofácil — Analisador e Gerador de Combinações")
st.markdown("Upload da planilha de resultados (Excel ou CSV). O app gera análises do último sorteio e permite gerar combinações com 5-12 números do último sorteio.")

# ---------- Helpers ----------
def extract_draw_numbers_from_row(row):
    # tenta extrair até 15 números numa linha (qualquer colunas numéricas)
    nums = []
    for v in row:
        if pd.isna(v):
            continue
        try:
            n = int(v)
            nums.append(n)
        except:
            # se string com separador
            if isinstance(v, str):
                parts = [p.strip() for p in v.replace(';',',').split(',') if p.strip()]
                for p in parts:
                    try:
                        nums.append(int(p))
                    except:
                        pass
    # dedupe e filtrar 1..25
    nums = [n for n in nums if 1 <= n <= 25]
    # se tiver mais que 15, pega primeiros 15 (assume arquivo bem formado)
    if len(nums) > 15:
        nums = nums[:15]
    return nums

def normalize_history(df):
    # transforma dataframe bruto em df com colunas: draw_index, date (opcional), n1..n15 sorted?, sum, pares, impares
    rows = []
    for idx, row in df.iterrows():
        nums = extract_draw_numbers_from_row(row.values)
        if len(nums) < 15:
            # ignora linhas incompletas
            continue
        nums_sorted = nums  # manter ordem original (se quiser ordenar, usar sorted(nums))
        s = sum(nums_sorted)
        pares = sum(1 for x in nums_sorted if x % 2 == 0)
        impares = 15 - pares
        rows.append({
            "draw_index": idx,
            "n": nums_sorted,
            "n1": nums_sorted[0],
            "n2": nums_sorted[1],
            "n3": nums_sorted[2],
            "n4": nums_sorted[3],
            "n5": nums_sorted[4],
            "n6": nums_sorted[5],
            "n7": nums_sorted[6],
            "n8": nums_sorted[7],
            "n9": nums_sorted[8],
            "n10": nums_sorted[9],
            "n11": nums_sorted[10],
            "n12": nums_sorted[11],
            "n13": nums_sorted[12],
            "n14": nums_sorted[13],
            "n15": nums_sorted[14],
            "sum": s,
            "pares": pares,
            "impares": impares
        })
    if not rows:
        return pd.DataFrame()
    expanded = pd.DataFrame(rows)
    return expanded

def compare_with_last(df_norm):
    # df_norm tem coluna 'n' (lista)
    last = df_norm.iloc[-1]["n"]
    results = []
    for i, row in df_norm.iterrows():
        common = len(set(row["n"]) & set(last))
        results.append({
            "draw_index": row["draw_index"],
            "common_with_last": common,
            "sum": row["sum"],
            "pares": row["pares"],
            "impares": row["impares"],
            **{f"n{j+1}": row[f"n{j+1}"] for j in range(15)}
        })
    return pd.DataFrame(results), last

def split_by_hits(df_comp):
    # cria dicionário de dataframes para hits 5..14
    groups = {}
    for hits in range(5, 15):
        groups[hits] = df_comp[df_comp["common_with_last"] == hits].reset_index(drop=True)
    return groups

def generate_combinations_from_last(last_draw, non_last, pick_from_last_k, total_even_needed, qty, max_attempts=200000):
    """
    last_draw: list of 15 numbers (last sorteio)
    non_last: list of numbers not in last draw (pool)
    pick_from_last_k: how many to use from last draw (5..12)
    total_even_needed: desired total count of even numbers in final 15
    qty: number of combos to generate
    returns list of sorted lists (size 15)
    """
    combos = set()
    last_set = set(last_draw)
    non_last = list(non_last)
    # Pre-calc parity sets
    last_even = [n for n in last_draw if n % 2 == 0]
    last_odd = [n for n in last_draw if n % 2 != 0]
    non_last_even = [n for n in non_last if n % 2 == 0]
    non_last_odd = [n for n in non_last if n % 2 != 0]

    attempts = 0
    while len(combos) < qty and attempts < max_attempts:
        attempts += 1
        # escolha aleatória dos k números do último sorteio
        chosen_from_last = tuple(sorted(random.sample(last_draw, pick_from_last_k)))
        # contador de pares já nessa parte
        pares_chosen = sum(1 for x in chosen_from_last if x % 2 == 0)
        need_from_non = 15 - pick_from_last_k
        pares_needed_from_non = total_even_needed - pares_chosen
        # Validar limites
        if pares_needed_from_non < 0 or pares_needed_from_non > need_from_non:
            continue
        # verificar disponibilidade
        if pares_needed_from_non > len(non_last_even):
            continue
        odds_needed_from_non = need_from_non - pares_needed_from_non
        if odds_needed_from_non > len(non_last_odd):
            continue
        # escolher pares e ímpares do non_last
        try:
            chosen_pairs = random.sample(non_last_even, pares_needed_from_non) if pares_needed_from_non>0 else []
            chosen_odds = random.sample(non_last_odd, odds_needed_from_non) if odds_needed_from_non>0 else []
        except ValueError:
            continue
        chosen_non = tuple(sorted(chosen_pairs + chosen_odds))
        combo = tuple(sorted(chosen_from_last + chosen_non))
        if combo in combos:
            continue
        combos.add(combo)
    combos_list = [list(c) for c in combos]
    return combos_list

# ---------- UI ----------
uploaded_file = st.file_uploader("Upload da planilha completa de resultados (XLSX, XLS ou CSV)", type=["xlsx","xls","csv"])
if uploaded_file is not None:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            raw = pd.read_csv(uploaded_file, header=0, dtype=str, keep_default_na=False)
        else:
            raw = pd.read_excel(uploaded_file, header=0, dtype=str)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        st.stop()

    st.write("Preview (primeiras linhas brutas):")
    st.dataframe(raw.head(6))

    df_norm = normalize_history(raw)
    if df_norm.empty:
        st.error("Não foi possível extrair linhas com 15 números cada. Verifique o formato do arquivo.")
        st.stop()

    st.success(f"Encontradas {len(df_norm)} linhas válidas (com 15 números).")

    df_comp, last_draw = compare_with_last(df_norm)
    st.markdown("### Último sorteio detectado")
    st.write(sorted(last_draw))
    st.markdown("### Estatísticas por sorteio (pares / ímpares / soma)")
    st.dataframe(df_norm[["draw_index","pares","impares","sum"]].tail(15))

    groups = split_by_hits(df_comp)

    st.markdown("### Quantidade de sorteios por número de acertos com o último sorteio (5..14)")
    counts = {k: len(v) for k,v in groups.items()}
    st.write(counts)

    # Botão para exportar as análises
    if st.button("Gerar arquivo Excel com análises (abas por acertos 5..14 + resumo)"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for hits, dfg in groups.items():
                sheet_name = f"acertos_{hits}"
                # se vazio criamos df vazio com colunas mínimas
                if dfg.empty:
                    pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    dfg.to_excel(writer, sheet_name=sheet_name, index=False)
            # resumo
            resumo = pd.DataFrame([{"acertos":k, "count":len(v)} for k,v in groups.items()])
            resumo.to_excel(writer, sheet_name="resumo", index=False)
            # incluir último sorteio em aba
            pd.DataFrame({"last_draw_sorted": [sorted(last_draw)]}).to_excel(writer, sheet_name="ultimo_sorteio", index=False)
            # incluir histórico normalizado
            df_norm.to_excel(writer, sheet_name="historico_normalizado", index=False)
            output.seek(0)
        st.download_button("Baixar arquivo Excel de análises", data=output, file_name=f"analise_lotofacil_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")
    st.markdown("## Gerar novas combinações a partir do último sorteio (usar arquivo gerado acima como referência opcional)")

    # upload do arquivo filtrado (opcional)
    uploaded_filtered = st.file_uploader("Upload opcional do arquivo com resultados filtrados (por exemplo acertos_5..14 gerado acima)", type=["xlsx","xls","csv"], key="filtered")
    if uploaded_filtered is not None:
        try:
            if uploaded_filtered.name.lower().endswith(".csv"):
                filtered_raw = pd.read_csv(uploaded_filtered, header=0, dtype=str, keep_default_na=False)
            else:
                filtered_raw = pd.read_excel(uploaded_filtered, header=0, dtype=str)
            st.write("Preview do arquivo filtrado:")
            st.dataframe(filtered_raw.head(5))
        except Exception as e:
            st.error(f"Erro ao ler o arquivo filtrado: {e}")

    # parâmetros para geração
    st.info("Defina o número de combinações a gerar e parâmetros (quantos números usar do último sorteio, quantos pares na combinação de 15).")
    qty = st.number_input("Quantidade de combinações a gerar", min_value=1, max_value=5000, value=100, step=1)
    pick_from_last_k = st.slider("Quantos números do último sorteio usar (k)", min_value=5, max_value=12, value=8)
    total_even_needed = st.slider("Quantidade total de números pares desejados na combinação (0..15)", min_value=0, max_value=15, value=7)
    seed = st.number_input("Random seed (0 para aleatório)", value=0, step=1)
    if seed != 0:
        random.seed(int(seed))

    if st.button("Gerar combinações"):
        # montar pool
        all_nums = set(range(1,26))
        last_set = set(last_draw)
        non_last = sorted(list(all_nums - last_set))
        st.write(f"Números não sorteados no último concurso ({len(non_last)}): {non_last}")

        combos = generate_combinations_from_last(last_draw=last_draw,
                                                 non_last=non_last,
                                                 pick_from_last_k=pick_from_last_k,
                                                 total_even_needed=total_even_needed,
                                                 qty=qty)

        if not combos:
            st.error("Não foi possível gerar combinações com os parâmetros fornecidos. Ajuste k, quantidade de pares, ou aumente tentativas.")
        else:
            # criar dataframe de combos
            combos_df = pd.DataFrame([{"combo_id": i+1,
                                       **{f"n{j+1}": combo[j] for j in range(15)},
                                       "soma": sum(combo),
                                       "pares": sum(1 for x in combo if x%2==0),
                                       "impares": sum(1 for x in combo if x%2!=0),
                                       "from_last_k": pick_from_last_k,
                                       "requested_parity": total_even_needed,
                                       "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                      } for i, combo in enumerate(combos)])
            st.success(f"Geradas {len(combos_df)} combinações.")
            st.dataframe(combos_df.head(20))

            # botão pra baixar
            output = io.BytesIO()
            meta = {"generated_from_last": sorted(last_draw), "params": {"qty":qty,"k":pick_from_last_k,"parity":total_even_needed,"seed": seed}, "created_at": datetime.now().isoformat()}
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                combos_df.to_excel(writer, sheet_name="combinacoes", index=False)
                pd.DataFrame([meta]).to_excel(writer, sheet_name="metadata", index=False)
                output.seek(0)
            st.download_button("Baixar combinações (.xlsx)", data=output, file_name=f"combinacoes_lotofacil_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")
st.markdown("Observações técnicas rápidas:")
st.markdown("""
- O app tenta extrair 15 números por linha do arquivo enviado. O formato mais simples: cada sorteio em uma linha com 15 colunas (n1..n15) ou com uma célula contendo '1,2,3,...,15'.
- Se o seu arquivo tem cabeçalhos tipo 'bl1..bl15' ele funciona direto. Se tiver outro formato, mantenha as linhas com exatamente 15 números, ou ajuste antes de subir.
- A geração de combinações usa amostragem aleatória respeitando o número de pares solicitado. Para gerar todas combinações possíveis seria combinatorialmente pesado; aqui usamos amostragem com limites para ser prático.
- Quer que eu converta para um backend FastAPI + frontend React? Digo na lata: eu monto se você quiser.
""")
