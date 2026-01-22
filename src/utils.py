import pandas as pd, json, os, yfinance as yf, numpy as np, streamlit as st
from datetime import datetime, timedelta
from bcb import sgs
# Funções de cálculos primários

def calcular_total_bonificacoes(df):
    """
    Retorna apenas a soma financeira do que entrou como Bonificação/Caixinha.
    Não precisa de loop complexo, apenas soma a coluna.
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
    FUNÇÃO INTERNA (começa com _): Contém a lógica pesada de Preço Médio.
    É usada pelas funções acima para evitar repetição de código.
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
        if tipo == 'Compra':
            carteira[ativo]['qtd'] += qtd
            carteira[ativo]['custo_total'] += total
        elif tipo == 'Bonificacao':
            carteira[ativo]['qtd'] += qtd
        elif tipo in ['Venda', 'Saque']:
            if carteira[ativo]['qtd'] > 0:
                pm = carteira[ativo]['custo_total'] / carteira[ativo]['qtd']
                custo_saida = pm * qtd
                
                if tipo == 'Venda':
                    lucro_operacao = total - custo_saida
                    lucro_acumulado += lucro_operacao
                
                carteira[ativo]['qtd'] -= qtd
                carteira[ativo]['custo_total'] -= custo_saida
    carteira_limpa = {k: v for k, v in carteira.items() if v['qtd'] > 0.000001}
    return carteira_limpa, lucro_acumulado

def calcular_resumo_ativos(df_transacoes):
    """
    Calcula a posição atual (Qtd e Preço Médio) de cada ativo.
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
        total = row['Total'] # Valor total da transação

        if ativo not in carteira:
            carteira[ativo] = {'qtd': 0.0, 'custo_total': 0.0}
        
        dados = carteira[ativo]

        # Lógica de Compra (Sobe PM)
        if tipo in ['Compra', 'Aporte', 'Reinvestimento', 'Bonificação']:
            # Na compra, somamos quantidade e custo
            dados['qtd'] += qtd
            dados['custo_total'] += total 
        
        # Lógica de Venda (Mantém PM)
        elif tipo in ['Venda', 'Resgate', 'Saque']:
            if dados['qtd'] > 0:
                # O Custo sai proporcionalmente ao PM atual
                pm_atual = dados['custo_total'] / dados['qtd']
                custo_saida = qtd * pm_atual
                
                dados['qtd'] -= qtd
                dados['custo_total'] -= custo_saida

    # Monta a tabela final
    linhas = []
    for ativo, dados in carteira.items():
        qtd = dados['qtd']
        custo = dados['custo_total']
        
        # Filtra ativos zerados (que você já vendeu tudo)
        if qtd > 0.0001:
            pm = custo / qtd
            linhas.append({
                "Ativo": ativo,
                "Quantidade": qtd,
                "Preço Médio": pm,
                "Total Investido": custo
            })
            
    df_resumo = pd.DataFrame(linhas)
    
    # Ordena alfabeticamente ou por valor (opcional)
    if not df_resumo.empty:
        df_resumo = df_resumo.sort_values("Ativo")
        
    return df_resumo

# Funções do rabalanceamento

METAS_REBAL = {
    'Renda Fixa': 0.50,
    'Stocks': 0.10,
    'ETF Internacional': 0.20,
    'Criptomoedas': 0.20
}

def classificar_ativo(cat_banco, nome_ativo):
    """Classifica o ativo nas 4 macro-categorias com base no nome/categoria."""
    texto = (str(cat_banco) + " " + str(nome_ativo)).lower()
    
    if any(x in texto for x in ["tesouro", "cdb", "lci", "lca", "debênture", "debenture", "caixinha", "renda fixa", "fii", "fundo imobiliario"]):
        return 'Renda Fixa'
    if any(x in texto for x in ["cripto", "bitcoin", "ether", "btc", "eth", "binance", "usdt"]):
        return 'Criptomoedas'
    if any(x in texto for x in ["stock", "reit", "ações eua", "acoes eua", "apple", "google", "microsoft"]):
        return 'Stocks'
    if any(x in texto for x in ["etf", "ivvb11", "sp500", "nasdaq", "wrld11", "voo", "qqq"]):
        return 'ETF Internacional'
    return 'Outros'

def preparar_dados_editor(carteira_atual, df_raw):
    """
    Prepara a lista inicial para o st.data_editor.
    Define automaticamente quem é 'Em Dólar' e a Classificação.
    """
    lista_ativos = []
    for ativo, dados_ativo in carteira_atual.items():
        cat_original = df_raw[df_raw['Ativo'] == ativo]['Categoria'].iloc[0] if 'Categoria' in df_raw.columns else "Geral"
        
        macro_cat = classificar_ativo(cat_original, ativo)
        
        is_usd = macro_cat in ['Stocks', 'Criptomoedas', 'ETF Internacional']
        
        lista_ativos.append({
            "Ativo": ativo,
            "Classificação": macro_cat,
            "Qtd Atual": float(dados_ativo['qtd']),
            "Preço Hoje": 0.0, 
            "Em Dólar?": is_usd
        })
    
    return pd.DataFrame(lista_ativos).sort_values(by="Classificação")

def calcular_rebalanceamento(df_editado, aporte, cotacao_dolar):
    """
    Recebe os dados digitados pelo usuário e faz toda a matemática.
    Retorna um dicionário com todos os resultados prontos para exibição.
    """
    df_calc = df_editado.copy()
    
    df_calc["Fator"] = df_calc["Em Dólar?"].apply(lambda x: cotacao_dolar if x else 1.0)
    df_calc["Total Atual (R$)"] = df_calc["Qtd Atual"] * df_calc["Preço Hoje"] * df_calc["Fator"]
    resumo_atual = df_calc.groupby("Classificação")["Total Atual (R$)"].sum().reset_index()
    
    patrimonio_atual = resumo_atual["Total Atual (R$)"].sum()
    patrimonio_final = patrimonio_atual + aporte
    lista_comparacao = []
    
    for categoria, meta_pct in METAS_REBAL.items():
        linha = resumo_atual[resumo_atual["Classificação"] == categoria]
        saldo_atual = linha["Total Atual (R$)"].sum() if not linha.empty else 0.0
        pct_atual = (saldo_atual / patrimonio_atual) if patrimonio_atual > 0 else 0
        meta_valor = patrimonio_final * meta_pct
        diferenca = meta_valor - saldo_atual
        
        lista_comparacao.append({
            "Categoria": categoria,
            "Pct Atual": pct_atual,
            "Meta Pct": meta_pct,
            "Diferença (R$)": diferenca
        })
        
    df_comparacao = pd.DataFrame(lista_comparacao)
    compras = df_comparacao[df_comparacao["Diferença (R$)"] > 1.0].copy()
    vendas = df_comparacao[df_comparacao["Diferença (R$)"] < -1.0].copy()
    
    outros = resumo_atual[~resumo_atual["Classificação"].isin(METAS_REBAL.keys())]
    valor_outros = outros["Total Atual (R$)"].sum() if not outros.empty else 0.0

    return {
        "df_comparacao": df_comparacao,
        "df_compras": compras,
        "df_vendas": vendas,
        "valor_outros": valor_outros,
        "patrimonio_atual": patrimonio_atual,
        "patrimonio_final": patrimonio_final
    }

# Funções de backup

def obter_caminho_db(nome_arquivo):
    """
    Função auxiliar para encontrar o arquivo correto independente de onde
    o terminal esteja aberto.
    """
    pasta_src = os.path.dirname(os.path.abspath(__file__))
    pasta_raiz = os.path.dirname(pasta_src)
    return os.path.join(pasta_raiz, 'db', nome_arquivo)

def obter_arquivo_banco():
    """Lê o arquivo binário do banco de dados para download."""
    caminho_db = obter_caminho_db('maindata.db')
    
    if os.path.exists(caminho_db):
        with open(caminho_db, 'rb') as f:
            return f.read()
    return None

def registrar_data_backup():
    """Salva apenas a data e hora atual no log."""
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    dados = {"ultimo_backup": agora}
    
    caminho_log = obter_caminho_db('backup_log.json')
    
    try:
        with open(caminho_log, 'w') as f:
            json.dump(dados, f)
    except Exception as e:
        print(f"Erro ao salvar log de backup: {e}")

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