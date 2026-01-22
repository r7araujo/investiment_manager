import pandas as pd, json, os, yfinance as yf, numpy as np, streamlit as st
from datetime import datetime, timedelta
from bcb import sgs
from constants import *

# Aqui estão as funções para 

# Funções de cálculos primários

def calcular_total_bonificacoes(df):
    """
    Retorna apenas a soma financeira do que entrou como Bonificação/Caixinha.
    """
    if df.empty:
        return 0.0
    total = df[df['Tipo'] == 'Bonificacao']['Qtd'].sum()
    return float(total)

def calcular_carteira_atual(df):
    """
    Retorna apenas o dicionário da carteira atual (Qtd e Custo de cada ativo).
    """
    carteira, _ = _processar_fluxo_caixa(df)
    return carteira

def calcular_lucro_realizado(df):
    """
    Retorna apenas o valor total do Lucro Realizado com vendas.
    """
    _, lucro = _processar_fluxo_caixa(df)
    return lucro

def _processar_fluxo_caixa(df):
    """
    Função interna para preço médio
    """
    if 'Data' in df.columns:
        df = df.sort_values('Data')
    
    carteira = {}
    lucro_acumulado = 0.0
    
    for index, row in df.iterrows():
        ativo = row['Ativo']
        tipo = row['Tipo']
        qtd = row['Qtd']
        total = row['Total']
        
        if ativo not in carteira:
            carteira[ativo] = {'qtd': 0.0, 'custo_total': 0.0}
        if tipo in ['Compra', 'Aporte', 'Reinvestimento']:
            carteira[ativo]['qtd'] += qtd
            carteira[ativo]['custo_total'] += total
        elif tipo == 'Bonificacao':
            carteira[ativo]['qtd'] += qtd
        elif tipo in ['Venda', 'Resgate']:
            if carteira[ativo]['qtd'] > 0:
                pm = carteira[ativo]['custo_total'] / carteira[ativo]['qtd']
                custo_saida = pm * qtd
                
                if tipo == 'Venda':     # Apenas vendas, lucro do resgate já foi registrado nas bonificações
                    lucro_operacao = total - custo_saida
                    lucro_acumulado += lucro_operacao
                
                carteira[ativo]['qtd'] -= qtd
                carteira[ativo]['custo_total'] -= custo_saida
    carteira_limpa = {k: v for k, v in carteira.items() if v['qtd'] > 0.000001}
    return carteira_limpa, lucro_acumulado

def calcular_resumo_ativos(df_transacoes):
    """
    Calcula Qtd e Preço Médio de cada ativo.
    Retorna um DataFrame pronto para exibição.
    """
    if df_transacoes.empty:
        return pd.DataFrame()

    carteira = {}
    # Estrutura: { 'PETR4': {'qtd': 100, 'custo_total': 2500} }

    # Garante que está ordenado por data para o cálculo funcionar
    df_sorted = df_transacoes.sort_values('Data')

    for _, row in df_sorted.iterrows():
        ativo = row['Ativo']
        tipo = row['Tipo']
        qtd = row['Qtd']
        total = row['Total']

        if ativo not in carteira:
            carteira[ativo] = {'qtd': 0.0, 'custo_total': 0.0}
        
        dados = carteira[ativo]

        # Lógica de Compra (Sobe PM)
        if tipo in ['Compra', 'Aporte', 'Reinvestimento', 'Bonificação']:
            dados['qtd'] += qtd
            dados['custo_total'] += total 
        
        # Lógica de Venda (Mantém PM)
        elif tipo in ['Venda', 'Resgate', 'Saque']:
            if dados['qtd'] > 0:
                pm_atual = dados['custo_total'] / dados['qtd']
                custo_saida = qtd * pm_atual
                dados['qtd'] -= qtd
                dados['custo_total'] -= custo_saida

    # Monta a tabela final
    linhas = []
    for ativo, dados in carteira.items():
        qtd = dados['qtd']
        custo = dados['custo_total']
        
        # Filtra ativos zerados
        if qtd >= 1e-8:
            pm = custo / qtd
            linhas.append({
                "Ativo": ativo,
                "Quantidade": qtd,
                "Preço Médio": pm,
                "Total Investido": custo
            })
            
    df_resumo = pd.DataFrame(linhas)
    if not df_resumo.empty:
        df_resumo = df_resumo.sort_values("Ativo")
        
    return df_resumo

# Funções do rabalanceamento

def classificar_ativo(categoria_input):
    # Seu mapa de classes (Pode vir de um arquivo constants.py ou estar aqui dentro)
    MAPA_CLASSES = {
        "Renda Fixa": ["Tesouro Direto", "CDB", "LCI/LCA", "Debêntures", "Caixinha"],
        "Renda Variável": ["Ações", "FIIs", "Stocks", "REITs", "ETF", "Criptomoedas", "BDR"]
    }

    # Remove espaços extras por segurança
    cat = str(categoria_input).strip()

    # 1. Se for Renda Fixa -> Retorna "Renda Fixa"
    if cat in MAPA_CLASSES["Renda Fixa"]:
        return "Renda Fixa"

    # 2. Se for Variável -> Retorna o PRÓPRIO nome (Ex: "Ações", "Stocks")
    if cat in MAPA_CLASSES["Renda Variável"]:
        return cat

    # Caso não encontre (Segurança)
    return "Outros"

def preparar_dados_editor(df_completo):
    """
    Recebe tabela com 'Ativo', 'Quantidade' e 'Categoria'.
    Monta visualização sem processamentos desnecessários.
    """
    lista_ativos = []
    
    if df_completo.empty:
        return pd.DataFrame(columns=["Ativo", "Classificação", "Qtd Atual", "Preço Hoje", "Em Dólar?"])

    for index, row in df_completo.iterrows():
        ativo = row['Ativo']
        qtd = float(row['Quantidade'])
        cat_original = row['Categoria'] # Vem exata do banco
        
        # Classificação direta
        macro_cat = classificar_ativo(cat_original)
        
        # Regra do Dólar (Ajuste se BDR ou ETF forem em Reais na sua visão)
        # Assumindo que Stocks, REITs e Cripto são dolarizados/precisam de conversão visual
        cats_dolar = ["Stocks", "REITs", "Criptomoedas", "ETF"] 
        is_usd = macro_cat in cats_dolar
        
        lista_ativos.append({
            "Ativo": ativo,
            "Classificação": macro_cat,
            "Qtd Atual": qtd,
            "Preço Hoje": 0.0, 
            "Em Dólar?": is_usd
        })
    
    return pd.DataFrame(lista_ativos).sort_values(by="Classificação")

def calcular_rebalanceamento(df_editado, aporte, cotacao_dolar, metas_usuario, valor_reserva=0.0):
    """
    Calcula rebalanceamento descontando a Reserva APENAS da categoria 'Renda Fixa'.
    """
    df_calc = df_editado.copy()
    
    # Cálculos Básicos
    df_calc["Fator"] = df_calc["Em Dólar?"].apply(lambda x: cotacao_dolar if x else 1.0)
    df_calc["Total Atual (R$)"] = df_calc["Qtd Atual"] * df_calc["Preço Hoje"] * df_calc["Fator"]
    
    # Agrupamento
    resumo_atual = df_calc.groupby("Classificação")["Total Atual (R$)"].sum().reset_index()
    
    # Lógica da Reserva de Emergência (Abate apenas da Renda Fixa)
    idx_rf = resumo_atual.index[resumo_atual["Classificação"] == "Renda Fixa"].tolist()
    
    if idx_rf:
        idx = idx_rf[0]
        valor_bruto = resumo_atual.at[idx, "Total Atual (R$)"]
        # Garante que não fica negativo
        valor_liquido = max(0.0, valor_bruto - valor_reserva)
        resumo_atual.at[idx, "Total Atual (R$)"] = valor_liquido

    # Totais Gerais
    patrimonio_atual = resumo_atual["Total Atual (R$)"].sum()
    patrimonio_final = patrimonio_atual + aporte
    
    # Comparação com as Metas
    lista_comparacao = []
    for categoria, meta_pct_raw in metas_usuario.items():
        meta_pct = float(meta_pct_raw) / 100.0
        
        linha = resumo_atual[resumo_atual["Classificação"] == categoria]
        saldo_atual = linha["Total Atual (R$)"].sum() if not linha.empty else 0.0
        
        pct_atual = (saldo_atual / patrimonio_atual) if patrimonio_atual > 0 else 0
        meta_valor_ideal = patrimonio_final * meta_pct
        diferenca = meta_valor_ideal - saldo_atual
        
        lista_comparacao.append({
            "Categoria": categoria,
            "Pct Atual": pct_atual * 100,
            "Meta Pct": meta_pct * 100,
            "Saldo Atual (R$)": saldo_atual,
            "Meta (R$)": meta_valor_ideal,
            "Diferença (R$)": diferenca
        })
        
    df_comparacao = pd.DataFrame(lista_comparacao)
    
    # Separação Compra/Venda
    compras = pd.DataFrame()
    vendas = pd.DataFrame()
    
    if not df_comparacao.empty:
        compras = df_comparacao[df_comparacao["Diferença (R$)"] > 1.0].sort_values("Diferença (R$)", ascending=False)
        vendas = df_comparacao[df_comparacao["Diferença (R$)"] < -1.0].sort_values("Diferença (R$)", ascending=True)
    
    # Valor em "Outros" (fora das metas)
    cats_meta = metas_usuario.keys()
    outros = resumo_atual[~resumo_atual["Classificação"].isin(cats_meta)]
    valor_outros = outros["Total Atual (R$)"].sum() if not outros.empty else 0.0

    return {
        "df_comparacao": df_comparacao,
        "df_compras": compras,
        "df_vendas": vendas,
        "valor_outros": valor_outros,
        "patrimonio_atual": patrimonio_atual,
        "patrimonio_final": patrimonio_final
    }
# Funções de meta

def calcular_progresso_metas(df_transacoes, lista_metas):
    """
    Recebe o DataFrame de transações e a lista de metas do banco.
    Retorna uma lista de dicionários com o progresso calculado.
    """
    resultados = []
    carteira_atual = calcular_carteira_atual(df_transacoes)
    total_investido = sum(item['custo_total'] for item in carteira_atual.values())
    total_proventos = df_transacoes[df_transacoes['Tipo'].isin(['Dividendo', 'JCP'])]['Total'].sum()
    for meta in lista_metas:
        id_meta, tipo, filtro, valor_alvo, data_limite, descricao = meta
        
        valor_atual = 0.0
        if tipo == 'Patrimônio Total':
            valor_atual = total_investido
            
        elif tipo == 'Total em Categoria':
            for ativo, dados in carteira_atual.items():
                cat_original = df_transacoes[df_transacoes['Ativo'] == ativo]['Categoria'].iloc[0]
                classe = classificar_ativo(cat_original, ativo)
                if filtro.lower() == classe.lower():
                    valor_atual += dados['custo_total']
                    
        elif tipo == 'Renda Passiva (Total)':
            valor_atual = total_proventos
        progresso_pct = (valor_atual / valor_alvo) if valor_alvo > 0 else 0
        if progresso_pct > 1.0: progresso_pct = 1.0
        
        falta = valor_alvo - valor_atual
        if falta < 0: falta = 0
        
        resultados.append({
            "id": id_meta,
            "titulo": descricao if descricao else f"{tipo} - {filtro}",
            "tipo": tipo,
            "valor_atual": valor_atual,
            "valor_alvo": valor_alvo,
            "falta": falta,
            "pct": progresso_pct,
            "data_limite": data_limite
        })
        
    return resultados