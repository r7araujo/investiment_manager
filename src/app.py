import streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from datetime import date
import database
MAPA_CLASSES = {
    "Renda Fixa": ["Tesouro Direto", "CDB", "LCI/LCA", "Debêntures", "Caixinha"],
    "Renda Variável": ["Ações", "FIIs", "Stocks", "REITs", "ETF", "Criptomoedas", "BDR"]
}
LISTA_CATEGORIAS = [item for sublist in MAPA_CLASSES.values() for item in sublist] + ["Outros"]

st.set_page_config(page_title="Meus Investimentos", layout="wide")
st.title("💰 Gerenciador de Investimentos")

tab_dash, tab_extrato, tab_registrar, tab_simular = st.tabs(["📊 Dashboard", "📑 Extrato", "⚙️ Registrador", "🔮 Simular"])

with tab_dash:
    st.header("Visão Geral & Performance")
    dados = database.consultar_extrato()
    if not dados:
        st.info("Cadastre operações na aba 'Gerenciar' para ver os indicadores.")
    else:
        colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Categoria", "Moeda", "Cambio", "Obs"]     
        df = pd.DataFrame(dados, columns=colunas_db)
        df = df.sort_values('Data') 

        carteira = {}           # Saldo atual de cada ativo
        lucro_realizado = 0.0   # Lucro obtido com vendas
        total_bonificacoes = 0.0 # Rendimento de Caixinha/Bonificações
        
        # Loop para os calculos
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
                total_bonificacoes += qtd  
            elif tipo == 'Venda':
                if carteira[ativo]['qtd'] > 0:
                    pm = carteira[ativo]['custo_total'] / carteira[ativo]['qtd'] # Preço medio
                    custo_da_venda = pm * qtd
                    # Lucro = Valor recebido na venda - Custo proporcional
                    lucro_operacao = total - custo_da_venda
                    lucro_realizado += lucro_operacao
                    # Baixa no estoque
                    carteira[ativo]['qtd'] -= qtd
                    carteira[ativo]['custo_total'] -= custo_da_venda
        # TOTAIS
        patrimonio_investido = sum(item['custo_total'] for item in carteira.values())        
        proventos_caixa = df[df['Tipo'].isin(['Dividendo', 'JCP'])]['Total'].sum()
        renda_passiva_total = proventos_caixa + total_bonificacoes

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Investido (Custo)", f"R$ {patrimonio_investido:,.2f}", help="Soma dos aportes menos o custo das vendas.")
        with col2:
            st.metric("Renda Passiva (Div + Caixinha)", f"R$ {renda_passiva_total:,.2f}", help="Dividendos, JCP e Rendimentos da Caixinha.")
        with col3:
            st.metric("Lucro Realizado (Vendas)", f"R$ {lucro_realizado:,.2f}", 
                      delta=f"{lucro_realizado:,.2f}" if lucro_realizado != 0 else None)
    
    st.divider()
    col_graf1, col_graf2 = st.columns([1, 2])

    with col_graf1:
        st.subheader("Alocação por Classe")
        
        df['Classe_Ativo'] = df['Categoria'].apply(lambda x: 'Renda Fixa' if x in MAPA_CLASSES['Renda Fixa'] else 'Renda Variável')
        
        df_ativos = df[df['Tipo'] == 'Compra']
        df_pizza = df_ativos.groupby('Classe_Ativo')['Total'].sum().reset_index()
        
        if not df_pizza.empty:
            fig_pizza = px.pie(
                df_pizza, 
                values='Total', 
                names='Classe_Ativo', 
                hole=0.5,
                color_discrete_sequence=['#36a2eb', '#ff6384']
            )
            fig_pizza.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Sem dados de compra.")

    with col_graf2:
        st.subheader("Evolução Patrimonial")
        
        if not df.empty:
            df['Data'] = pd.to_datetime(df['Data'])
            df_sorted = df.sort_values('Data')
            data_inicio = df_sorted['Data'].min().replace(day=1)
            data_hoje = pd.Timestamp.now().replace(day=1)
            data_futura_minima = data_inicio + pd.DateOffset(months=12)
            data_fim = max(data_hoje, data_futura_minima)
            date_range = pd.date_range(start=data_inicio, end=data_fim, freq='MS')

            eixo_datas = []
            eixo_aportes = []
            eixo_acumulado = [] # Linha do total investido
            
            # Variaveis de estado (para carregar o saldo mes a mes)
            carteira_temp = {} 
            
            # Loop mes a mes
            for data_mes in date_range:
                # Pega só o que aconteceu neste mes
                mask_mes = (df_sorted['Data'].dt.year == data_mes.year) & (df_sorted['Data'].dt.month == data_mes.month)
                transacoes_mes = df_sorted[mask_mes]
                
                aporte_do_mes = 0.0
                
                # Processa as transacoes do mes para atualizar a carteira
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
                        aporte_do_mes += total # Soma na barra de aporte
                        
                    elif tipo == 'Bonificacao':
                        carteira_temp[ativo]['qtd'] += qtd
                        # Custo zero, não soma no aporte financeiro
                        
                    elif tipo == 'Venda':
                        if carteira_temp[ativo]['qtd'] > 0:
                            # Abate do custo proporcional
                            pm = carteira_temp[ativo]['custo_total'] / carteira_temp[ativo]['qtd']
                            custo_da_venda = pm * qtd
                            
                            carteira_temp[ativo]['qtd'] -= qtd
                            carteira_temp[ativo]['custo_total'] -= custo_da_venda
                            # Nota: Venda reduz a linha de acumulado, mas não gera barra negativa
                
                # Calcula quanto tenho investido (Custo) no final deste mes
                total_investido_mes = sum(item['custo_total'] for item in carteira_temp.values())
                
                eixo_datas.append(data_mes)
                eixo_aportes.append(aporte_do_mes)
                eixo_acumulado.append(total_investido_mes)

            fig_evolucao = go.Figure()
            fig_evolucao.add_trace(go.Bar(
                x=eixo_datas, 
                y=eixo_aportes, 
                name='Aporte Mensal',
                marker_color='rgba(54, 162, 235, 0.6)'
            ))
            fig_evolucao.add_trace(go.Scatter(
                x=eixo_datas, 
                y=eixo_acumulado, 
                name='Total Investido (Custo)',
                mode='lines+markers',
                line=dict(color='#4bc0c0', width=3)
            ))
            
            fig_evolucao.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=20, b=20, l=20, r=20),
                xaxis=dict(
                    tickformat="%b/%Y", 
                    dtick="M1"
                )
            )
            
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.info("Sem dados para gerar gráfico de evolução.")
    st.divider()
    lista_posicao = []

    for ativo, dados_ativo in carteira.items():
        if dados_ativo['custo_total'] > 0.01: # Filtra apenas o que tem saldo
            # Busca categoria no DF original (primeira ocorrência)
            cat_original = df[df['Ativo'] == ativo]['Categoria'].iloc[0] if 'Categoria' in df.columns else "Outros"
            
            # Define Classe
            classe = 'Renda Fixa' if cat_original in MAPA_CLASSES['Renda Fixa'] else 'Renda Variável'
            
            lista_posicao.append({
                'Ativo': ativo,
                'Categoria': cat_original,
                'Classe': classe,
                'Total Investido': dados_ativo['custo_total']
            })

    df_posicao = pd.DataFrame(lista_posicao)

    st.divider()
    
    # --- BLOCO DE DETALHAMENTO (PIZZAS + EXTRATO) ---
    
    # 1. Preparar dados consolidados
    lista_posicao = []
    for ativo, dados_ativo in carteira.items():
        if dados_ativo['custo_total'] > 0.01:
            cat_original = df[df['Ativo'] == ativo]['Categoria'].iloc[0] if 'Categoria' in df.columns else "Outros"
            classe = 'Renda Fixa' if cat_original in MAPA_CLASSES['Renda Fixa'] else 'Renda Variável'
            
            lista_posicao.append({
                'Ativo': ativo,
                'Categoria': cat_original,
                'Classe': classe,
                'Total Investido': dados_ativo['custo_total']
            })
    
    df_posicao = pd.DataFrame(lista_posicao)
    
    if not df_posicao.empty:
        col_grafico, col_detalhes = st.columns([1.5, 1])
        with col_grafico:
            st.subheader("Alocação por Categoria")

            tipo_visualizacao = st.radio(
                "Selecione a Classe:", 
                ["Renda Fixa", "Renda Variável"], 
                horizontal=True
            )
            df_pizza = df_posicao[df_posicao['Classe'] == tipo_visualizacao]
            if not df_pizza.empty:
                paleta = px.colors.sequential.RdBu if tipo_visualizacao == 'Renda Fixa' else px.colors.sequential.Oranges
                fig = px.pie(
                    df_pizza, 
                    values='Total Investido', 
                    names='Categoria', 
                    hole=0.5,
                    color_discrete_sequence=paleta
                )
                fig.update_layout(
                    showlegend=True,
                    margin=dict(t=20, b=20, l=0, r=0),
                    legend=dict(
                        orientation="v",    
                        yanchor="top",
                        y=1,                
                        xanchor="left",
                        x=1.05              
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Você não possui ativos de {tipo_visualizacao}.")
        with col_detalhes:
            st.subheader("🔍 Detalhes")
            cat_unicas = sorted(df_posicao['Categoria'].unique().tolist())
            filtro_tabela = st.selectbox("Filtrar Tabela:", ["Todos"] + cat_unicas)
            
            if filtro_tabela != "Todos":
                df_exibir = df_posicao[df_posicao['Categoria'] == filtro_tabela]
            else:
                df_exibir = df_posicao 
            
            st.dataframe(
                df_exibir[['Ativo', 'Categoria', 'Total Investido']].sort_values('Total Investido', ascending=False),
                hide_index=True,
                use_container_width=True,
                height=400,
                column_config={
                    "Total Investido": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Ativo": st.column_config.TextColumn(width="small")
                }
            )
with tab_extrato:
    st.header("Histórico de Transações")
    
    with st.expander("Filtros", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            data_inicial = st.date_input("Data Inicial", date(2023, 1, 1))
            data_final = st.date_input("Data Final", date.today())
        with col_f2:
            tipos_opcoes = ["Compra", "Venda", "Dividendo", "JCP", "Taxa", "Cambio", "Bonificacao"]
            tipos_selecionados = st.multiselect("Filtrar Tipo", tipos_opcoes, default=tipos_opcoes)

    dados = database.consultar_extrato()
    
    if dados:
        qtd_cols = len(dados[0])
        if qtd_cols == 12:
            colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Categoria", "Moeda", "Cambio", "Obs"]
        else:
            colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Moeda", "Cambio", "Obs"]
        
        df = pd.DataFrame(dados, columns=colunas_db)
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        
        mask_data = (df['Data'] >= data_inicial) & (df['Data'] <= data_final)
        mask_tipo = df['Tipo'].isin(tipos_selecionados)
        df_filtrado = df.loc[mask_data & mask_tipo]
        cols_visuais = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Moeda", "Cambio", "Obs"]
        if "Categoria" in df_filtrado.columns:
            cols_visuais.insert(3, "Categoria")
            
        st.dataframe(
            df_filtrado[cols_visuais], 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Preço": st.column_config.NumberColumn(format="%.2f"),
                "Total": st.column_config.NumberColumn(format="%.2f"),
                "Cambio": st.column_config.NumberColumn(format="%.2f"),
                "Qtd": st.column_config.NumberColumn(format="%.8f"),
            }
        )
    else:
        st.warning("Nenhum dado encontrado.")

with tab_registrar:
    st.header("Controle de Registros")
    col_add, col_rm = st.columns([2, 1])

    with col_add:
        st.subheader("Adicionar Novo")
        with st.form("novo_lancamento", clear_on_submit=True):
            data_op = st.date_input("Data", date.today())
            
            c1, c2 = st.columns(2)
            with c1:
                ativo = st.text_input("Ativo").upper()
            with c2:
                tipo = st.selectbox("Tipo", ["Compra", "Venda", "Dividendo", "JCP", "Taxa", "Cambio", "Bonificacao"])
            
            col_cat1, col_cat2 = st.columns(2)
            with col_cat1:
                corretora = st.selectbox("Corretora", ["XP", "Binance", "Nubank", "Outra"])
            with col_cat2:
                categoria = st.selectbox("Categoria do Ativo", LISTA_CATEGORIAS)

            moeda = st.radio("Moeda", ["BRL", "USD"], horizontal=True)
            cotacao = st.number_input("Câmbio (Use 1.0 se for BRL)", value=1.0, min_value=0.01, step=0.01)
            
            c3, c4 = st.columns(2)
            with c3:
                qtd = st.number_input("Quantidade", min_value=0.0, step=0.00000001, format="%.8f")
            with c4:
                preco = st.number_input("Preço Unitário", min_value=0.0, step=0.01, format="%.2f")
            
            obs = st.text_area("Observação")
            
            btn_salvar = st.form_submit_button("Salvar Transação")
            if btn_salvar:
                if not ativo:
                    st.error("O campo Ativo é obrigatório.")
                else:
                    database.add_transacao(
                        data_op, ativo, tipo, qtd, preco, corretora, 
                        categoria, 
                        moeda, cotacao, obs
                    )
                    st.success("Registro salvo com sucesso!")

    with col_rm:
        st.subheader("Remover Item")
        id_del = st.number_input("ID da Transação", min_value=0, step=1)
        if st.button("Apagar Registro"):
            database.del_transacao(id_del)
            st.success(f"Registro ID {id_del} removido.")