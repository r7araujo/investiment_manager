import pandas as pd, json, os, yfinance as yf, numpy as np, streamlit as st
from datetime import datetime, timedelta
from bcb import sgs
from constants import *

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

    carteira = {}   # Estrutura: { 'PETR4': {'qtd': 100, 'custo_total': 2500} }
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

def calcular_evolucao_patrimonial(df_sorted, date_range):
    """
    Calcula a evolução patrimonial mensal.
    Retorna eixos X (datas), Y1 (aportes mensais) e Y2 (total acumulado).
    """
    eixo_datas = []
    eixo_aportes = []
    eixo_acumulado = [] 
    carteira_temp = {} 

    for data_mes in date_range:
        # Filtra transações deste mes específico
        mask_mes = (df_sorted['Data'].dt.year == data_mes.year) & (df_sorted['Data'].dt.month == data_mes.month)
        transacoes_mes = df_sorted[mask_mes]
        
        aporte_do_mes = 0.0
        
        # Processa cada transação do mês
        for _, row in transacoes_mes.iterrows():
            ativo = row['Ativo']
            tipo = row['Tipo']
            qtd = row['Qtd']
            total = row['Total']
            
            if ativo not in carteira_temp:
                carteira_temp[ativo] = {'qtd': 0.0, 'custo_total': 0.0}
            
            if tipo == 'Compra':
                carteira_temp[ativo]['qtd'] += qtd
                carteira_temp[ativo]['custo_total'] += total
                aporte_do_mes += total 
                
            elif tipo == 'Bonificacao':
                carteira_temp[ativo]['qtd'] += qtd
                
            elif tipo == 'Venda':
                if carteira_temp[ativo]['qtd'] > 0:
                    pm = carteira_temp[ativo]['custo_total'] / carteira_temp[ativo]['qtd']
                    custo_da_venda = pm * qtd
                    carteira_temp[ativo]['qtd'] -= qtd
                    carteira_temp[ativo]['custo_total'] -= custo_da_venda

            elif tipo == 'Saque':
                if carteira_temp[ativo]['qtd'] > 0:
                    pm = carteira_temp[ativo]['custo_total'] / carteira_temp[ativo]['qtd']
                    custo_saque = pm * qtd
                    carteira_temp[ativo]['qtd'] -= qtd
                    carteira_temp[ativo]['custo_total'] -= custo_saque

        total_investido_mes = sum(item['custo_total'] for item in carteira_temp.values())
        
        # Salva nas listas para o gráfico after month processing
        eixo_datas.append(data_mes)
        eixo_aportes.append(aporte_do_mes)
        eixo_acumulado.append(total_investido_mes)
        
    return eixo_datas, eixo_aportes, eixo_acumulado

def calcular_alocacao_por_classe(df):
    """
    Agrupa o total investido por Classe de Ativo (Renda Fixa x Variavel).
    Retorna DataFrame pronto para o gráfico de Pizza.
    """
    df_temp = df.copy()
    df_temp['Classe_Ativo'] = df_temp['Categoria'].apply(
        lambda x: 'Renda Fixa' if x in MAPA_CLASSES['Renda Fixa'] else 'Renda Variável'
    )
    
    # Filtra apenas Compras para ver proporção de entrada (ou poderia ser saldo atual,
    # mas mantendo a lógica original do app.py que filtrava 'Compra')
    df_ativos = df_temp[df_temp['Tipo'] == 'Compra']
    
    return df_ativos.groupby('Classe_Ativo')['Total'].sum().reset_index()

def gerar_tabela_alocacao(carteira, df_transacoes):
    """
    Gera a tabela de alocação detalhada por ativo e suas categorias.
    """
    lista_posicao = []
    
    # Cache simples de categorias para não buscar no DF a cada iteração de forma lenta
    # Cria um dict: { 'PETR4': 'Ações', 'TESOURO': 'Renda Fixa' ... }
    # Pega o último registro de categoria válido para cada ativo
    mapa_categorias = {}
    if not df_transacoes.empty and 'Categoria' in df_transacoes.columns:
        df_unicos = df_transacoes[['Ativo', 'Categoria']].drop_duplicates('Ativo', keep='last')
        mapa_categorias = dict(zip(df_unicos['Ativo'], df_unicos['Categoria']))

    for ativo, dados_ativo in carteira.items():
        if dados_ativo['custo_total'] > 0.01:
            cat_original = mapa_categorias.get(ativo, "Outros")
            classe = classificar_ativo(cat_original) # Usa a função já existente
            
            # Ajuste fino: Se a função retornar o próprio nome (Ex: Ações), converte para Macro
            if classe not in ['Renda Fixa', 'Renda Variável']:
                 # Se não é Renda Fixa, assume Variável para o gráfico macro
                 classe = 'Renda Variável' if cat_original not in MAPA_CLASSES['Renda Fixa'] else 'Renda Fixa'

            lista_posicao.append({
                'Ativo': ativo,
                'Categoria': cat_original,
                'Classe': classe,
                'Total Investido': dados_ativo['custo_total']
            })
    
    return pd.DataFrame(lista_posicao)

def calcular_cenarios_simulacao(qtd_atual, preco_simulado, pm_atual):
    """
    Gera cenários de venda parcial (25%, 50%, 75%, 100%).
    """
    cenarios = [0.25, 0.50, 0.75, 1.0]
    lista_cenarios = []
    
    for p in cenarios:
        q = qtd_atual * p
        v = q * preco_simulado
        c = q * pm_atual
        l = v - c
        lista_cenarios.append({
            "Cenário": f"Vender {int(p*100)}%",
            "Qtd": q,
            "Receba (R$)": v,
            "Lucro (R$)": l
        })
    
    return pd.DataFrame(lista_cenarios)

# Funções que puxam dados externos

def obter_cotacao_online(lista_tickers):
    """
    Busca cotação online via yfinance.
    Tenta em lote primeiro. Se falhar, tenta individualmente.
    """
    if not lista_tickers:
        return {}
    
    # Dicionário de resultados
    cotacoes = {}
    
    # 1. Tratamento inicial de tickers
    mapa_tickers = {} # { 'BTC': 'BTC-BRL', 'PETR4': 'PETR4.SA' }
    
    for t in lista_tickers:
        t_str = str(t).upper().strip()
        t_final = t_str
        
        # Lógica de sufixos
        if t_str in ["BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX"]:
             t_final = f"{t_str}-BRL"
        elif len(t_str) >= 5 and t_str[-1].isdigit() and ".SA" not in t_str:
             t_final = f"{t_str}.SA"
             
        mapa_tickers[t] = t_final

    lista_para_yahoo = list(mapa_tickers.values())
    try:
        dados = yf.download(lista_para_yahoo, period="1d", progress=False)['Close']
        if not dados.empty:
            if isinstance(dados, pd.Series):
                 val = dados.iloc[-1]
                 if not pd.isna(val):
                     tk_unico = list(mapa_tickers.keys())[0]
                     cotacoes[tk_unico] = float(val)
            elif isinstance(dados, pd.DataFrame):
                for t_orig, t_yahoo in mapa_tickers.items():
                    if t_yahoo in dados.columns:
                        val = dados[t_yahoo].iloc[-1]
                        if not pd.isna(val):
                            cotacoes[t_orig] = float(val)
    except Exception as e:
        st.write(f"Erro no download em lote: {e}")
    # Fallback: Verifica quem ficou sem cotação e tenta individualmente
    faltantes = [t for t in lista_tickers if t not in cotacoes]
    if faltantes:
        for t in faltantes:
            t_yahoo = mapa_tickers[t]
            val = _buscar_ticker_individual(t_yahoo)
            # Se falhou e era cripto BRL, tenta USD
            if val is None and t_yahoo.endswith("-BRL"):
                t_usd = t_yahoo.replace("-BRL", "-USD")
                val_usd = _buscar_ticker_individual(t_usd)
                if val_usd is not None:
                     # Converte para BRL (pega dolar hoje aprox ou do yahoo)
                     dolar = _buscar_ticker_individual("BRL=X") # Yahoo: BRL=X é USD/BRL? Não, USDBRL=X
                     if not dolar: dolar = _buscar_ticker_individual("USDBRL=X")
                     val = val_usd * dolar
            
            if val is not None:
                cotacoes[t] = val
                
    return cotacoes

def _buscar_ticker_individual(ticker):
    """Helper para buscar 1 ticker específico"""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except:
        return None
    return None

def gerar_painel_rentabilidade(carteira, df_transacoes):
    """
    Monta a tabela comparando PM x Cotação Atual.
    """
    
    # Filtra o que é Renda Variável para buscar cotação
    # Precisa saber a categoria de cada ativo da carteira
    mapa_categorias = {}
    if not df_transacoes.empty and 'Categoria' in df_transacoes.columns:
        df_unicos = df_transacoes[['Ativo', 'Categoria']].drop_duplicates('Ativo', keep='last')
        mapa_categorias = dict(zip(df_unicos['Ativo'], df_unicos['Categoria']))
    
    ativos_rv = []
    
    # 2. Identifica quem é Renda Variável de fato
    for ativo, dados in carteira.items():
        if dados['qtd'] < 0.000001: continue
        cat = mapa_categorias.get(ativo, "Outros")
        classe_macro = classificar_ativo(cat)
        if classe_macro != "Renda Fixa" and classe_macro != "Outros":
            ativos_rv.append(ativo)
    cotacoes = obter_cotacao_online(ativos_rv)
    lista_rentabilidade = []
    total_atual_carteira = 0.0
    total_custo_carteira = 0.0
    for ativo in ativos_rv:
        dados = carteira[ativo]
        qtd = dados['qtd']
        custo_total = dados['custo_total']
        pm = custo_total / qtd
        
        usou_fallback = False
        if ativo in cotacoes:
             cotacao_atual = cotacoes[ativo]
        else:
             cotacao_atual = pm 
             usou_fallback = True
        
        valor_atual_ativo = qtd * cotacao_atual
        lucro_rs = valor_atual_ativo - custo_total
        lucro_pct = (lucro_rs / custo_total) * 100 if custo_total > 0 else 0.0
        
        total_atual_carteira += valor_atual_ativo
        total_custo_carteira += custo_total
        
        lista_rentabilidade.append({
            "Ativo": ativo,
            "Qtd": qtd,
            "PM": pm,
            "Cotação Atual": cotacao_atual,
            "Valor Atual": valor_atual_ativo,
            "Lucro (R$)": lucro_rs,
            "Var (%)": lucro_pct,
            "Status": "⚠️ Offline" if usou_fallback else "✅ Online"
        })
        
    df_rent = pd.DataFrame(lista_rentabilidade)
    if not df_rent.empty:
        df_rent = df_rent.sort_values(by="Var (%)", ascending=False)
        
    resumo_geral = {
        "custo_total": total_custo_carteira,
        "valor_atual": total_atual_carteira,
        "lucro_total_rs": total_atual_carteira - total_custo_carteira,
        "lucro_total_pct": ((total_atual_carteira - total_custo_carteira) / total_custo_carteira * 100) if total_custo_carteira > 0 else 0
    }
    
    return df_rent, resumo_geral

# Funções do rebalanceamento

def classificar_ativo(categoria_input, *args):
    cat = str(categoria_input).strip()

    # 1. Se for Renda Fixa -> Retorna "Renda Fixa"
    if cat in MAPA_CLASSES["Renda Fixa"]:
        return "Renda Fixa"

    # 2. Se for Variável -> Retorna o PRÓPRIO nome (Ex: "Ações", "Stocks")
    if cat in MAPA_CLASSES["Renda Variável"]:
        return cat

    # Caso não encontre
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
        # Assumindo que Stocks, REITs e ETF são dolarizados/precisam de conversão visual
        cats_dolar = ["Stocks", "REITs", "ETF"] 
        is_usd = macro_cat in cats_dolar
        
        lista_ativos.append({
            "Ativo": ativo,
            "Classificação": macro_cat,
            "Qtd Atual": qtd,
            "Preço Hoje": 0.0, 
            "Em Dólar?": is_usd
        })
    
    return pd.DataFrame(lista_ativos).sort_values(by="Classificação")

def unificar_dados_com_categorias(df_carteira, df_raw):
    """
    Cruza o resumo da carteira com as categorias vindas do extrato.
    """
    # Recupera a categoria EXATA do banco (sem normalização)
    # Pega a última categoria registrada para o ativo
    tab_cat = df_raw[['Ativo', 'Categoria']].drop_duplicates('Ativo', keep='last')
    
    # Cruza: Tabela de Quantidades + Tabela de Categorias
    df_completo = df_carteira.merge(tab_cat, on='Ativo', how='left')
    df_completo['Categoria'] = df_completo['Categoria'].fillna("Outros")
    
    return df_completo

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