import streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
from datetime import date
from utils import *
from database import *
inicializar_tabela_metas()
MAPA_CLASSES = {
    "Renda Fixa": ["Tesouro Direto", "CDB", "LCI/LCA", "Debêntures", "Caixinha"],
    "Renda Variável": ["Ações", "FIIs", "Stocks", "REITs", "ETF", "Criptomoedas", "BDR"]
}
LISTA_CATEGORIAS = [item for sublist in MAPA_CLASSES.values() for item in sublist] + ["Outros"]

st.set_page_config(page_title="Meus Investimentos", layout="wide")
st.title("💰 Gerenciador de Investimentos")

tab_dash, tab_extrato, tab_registrar, tab_simular, tab_rebal, tab_metas = st.tabs([
    "📊 Dashboard", "📑 Extrato", "⚙️ Registrador", "🔮 Simular", "⚖️ Rebalanceador", "🎯 Metas"
    ])


with tab_dash:
    st.header("Visão Geral & Performance")
    dados = consultar_extrato()
    
    if not dados:
        st.info("Cadastre operações na aba 'Gerenciar' para ver os indicadores.")
    else:
        colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Categoria", "Moeda", "Cambio", "Obs"]
        if len(dados[0]) != 12: colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Moeda", "Cambio", "Obs"]
        df = pd.DataFrame(dados, columns=colunas_db)
        df['Data'] = pd.to_datetime(df['Data'])
        carteira = calcular_carteira_atual(df)
        lucro_realizado = calcular_lucro_realizado(df)
        total_bonificacoes = calcular_total_bonificacoes(df)
        patrimonio_investido = sum(item['custo_total'] for item in carteira.values())
        proventos_caixa = df[df['Tipo'].isin(['Dividendo', 'JCP'])]['Total'].sum()
        renda_passiva_total = proventos_caixa + total_bonificacoes
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Investido (Custo)", f"R$ {patrimonio_investido:,.2f}")
        with col2:
            st.metric("Renda Passiva (Div + Caixinha)", f"R$ {renda_passiva_total:,.2f}")
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
                # 1. Conversão de Data (Garante que funciona)
                df['Data'] = pd.to_datetime(df['Data'])
                df_sorted = df.sort_values('Data')
                
                # 2. Define o período do gráfico
                data_inicio = df_sorted['Data'].min().replace(day=1)
                data_hoje = pd.Timestamp.now().replace(day=1)
                
                # Garante pelo menos 12 meses de visão
                data_futura_minima = data_inicio + pd.DateOffset(months=12)
                data_fim = max(data_hoje, data_futura_minima)
                
                date_range = pd.date_range(start=data_inicio, end=data_fim, freq='MS')
                
                # Listas para o grafico
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
                    
                    # Salva nas listas para o gráfico
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
                    xaxis=dict(tickformat="%b/%Y", dtick="M1")
                )
                
                st.plotly_chart(fig_evolucao, use_container_width=True)
            else:
                st.info("Sem dados para gerar gráfico de evolução.")
    st.divider()
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
            tipos_opcoes = ["Compra", "Venda", "Saque", "Dividendo", "JCP", "Taxa", "Cambio", "Bonificacao"]
            tipos_selecionados = st.multiselect("Filtrar Tipo", tipos_opcoes, default=tipos_opcoes)

    dados = consultar_extrato()
    
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
                tipo = st.selectbox("Tipo", ["Compra", "Venda", "Saque", "Dividendo", "JCP", "Taxa", "Cambio", "Bonificacao"])
            
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
                    add_transacao(
                        data_op, ativo, tipo, qtd, preco, corretora, 
                        categoria, 
                        moeda, cotacao, obs
                    )
                    st.success("Registro salvo com sucesso!")

    with col_rm:
        st.subheader("Remover Item")
        id_del = st.number_input("ID da Transação", min_value=0, step=1)
        if st.button("Apagar Registro"):
            del_transacao(id_del)
            st.success(f"Registro ID {id_del} removido.")
        st.divider()

        st.subheader("💾 Backup e Segurança")
        arquivo_bytes = obter_arquivo_banco()
        
        if arquivo_bytes:
            st.download_button(
                label="📥 Baixar Backup (.db)",
                data=arquivo_bytes,
                file_name="maindata_backup.db",
                mime="application/x-sqlite3",
                on_click=registrar_data_backup,
                help="Salva uma cópia do banco de dados na pasta Downloads."
            )
            st.caption("O arquivo será salvo na sua pasta de Downloads padrão.")
        else:
            st.error("Erro: Arquivo 'maindata.db' não encontrado.")

with tab_simular:

    st.header("🔮 Simulador de Vendas & Lucro")
    
    dados = consultar_extrato()
    
    if not dados:
        st.warning("Sem dados para simular.")
    else:
        colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Categoria", "Moeda", "Cambio", "Obs"]
        if len(dados[0]) != 12: colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Moeda", "Cambio", "Obs"]
        df = pd.DataFrame(dados, columns=colunas_db)
        carteira_sim = calcular_carteira_atual(df) 
        ativos_disponiveis = sorted(list(carteira_sim.keys()))
        
        if not ativos_disponiveis:
            st.info("Você não possui ativos em carteira para simular.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                ativo_sel = st.selectbox("Selecione o Ativo", sorted(ativos_disponiveis))
            dados_ativo = carteira_sim[ativo_sel]
            qtd_atual = dados_ativo['qtd']
            custo_total = dados_ativo['custo_total']
            pm_atual = custo_total / qtd_atual if qtd_atual > 0 else 0
            
            with c2:
                preco_simulado = st.number_input("Preço de Venda (Cotação Atual)", value=float(round(pm_atual, 2)), min_value=0.01, step=0.01)
            
            with c3:
                st.metric("Seu Preço Médio (PM)", f"R$ {pm_atual:,.2f}")

            st.divider()
            st.subheader("Cenário vendendo 100%")
            
            if qtd_atual > 0:
                valor_venda_bruto = qtd_atual * preco_simulado
                custo_proporcional = qtd_atual * pm_atual
                lucro_bruto = valor_venda_bruto - custo_proporcional
                roi_pct = (lucro_bruto / custo_proporcional) * 100 if custo_proporcional > 0 else 0
                col_res1, col_res2, col_res3 = st.columns(3)
                
                with col_res1:
                    st.metric("Valor Total da Venda", f"R$ {valor_venda_bruto:,.2f}")
                
                with col_res2:
                    st.metric(
                        "Lucro/Prejuízo Estimado", 
                        f"R$ {lucro_bruto:,.2f}",
                        delta=f"{roi_pct:.2f}%",
                        delta_color="normal"
                    )
                
                with col_res3:
                    st.markdown(f"""
                    **Resumo da Operação:**
                    - Você venderia **{qtd_atual:,.4f}** unidades.
                    """)
                st.markdown("### ⚡ Cenários Rápidos")
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
                
                df_cenarios = pd.DataFrame(lista_cenarios)
                st.dataframe(
                    df_cenarios, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Receba (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Lucro (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Qtd": st.column_config.NumberColumn(format="%.4f"),
                    }
                )

with tab_rebal:
    st.header("⚖️ Rebalanceamento Automático")
    
    dados = consultar_extrato()
    
    if not dados:
        st.warning("Cadastre operações primeiro.")
    else:
        colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Categoria", "Moeda", "Cambio", "Obs"]
        if len(dados[0]) != 12: colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Moeda", "Cambio", "Obs"]
        df_raw = pd.DataFrame(dados, columns=colunas_db)
        
        carteira_atual = calcular_carteira_atual(df_raw)
        
        if not carteira_atual:
            st.info("Carteira zerada.")
        else:
            st.markdown("### 1️⃣ Parâmetros")
            c1, c2 = st.columns(2)
            with c1:
                cotacao_dolar = st.number_input("🇺🇸 Dólar Hoje (R$)", value=5.00, step=0.01, format="%.2f")
            with c2:
                aporte = st.number_input("💰 Aporte Novo (R$)", min_value=0.0, step=100.0)

            st.divider()
            st.markdown("### 2️⃣ Atualize os Preços")
            
            df_editor = preparar_dados_editor(carteira_atual, df_raw)
            
            df_editado = st.data_editor(
                df_editor,
                column_config={
                    "Ativo": st.column_config.TextColumn(disabled=True),
                    "Classificação": st.column_config.TextColumn(disabled=True),
                    "Qtd Atual": st.column_config.NumberColumn(disabled=True, format="%.4f"),
                    "Preço Hoje": st.column_config.NumberColumn(min_value=0.0, step=0.01, required=True, format="%.2f"),
                    "Em Dólar?": st.column_config.CheckboxColumn(help="Marque se o preço é em US$.")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_rebal_clean"
            )
            
            if st.button("🔄 Calcular Rebalanceamento", type="primary"):
                if df_editado["Preço Hoje"].min() <= 0:
                    st.error("⚠️ Preencha todos os preços.")
                else:
                    resultados = calcular_rebalanceamento(df_editado, aporte, cotacao_dolar)            
                    st.divider()
                    st.subheader("📊 Diagnóstico (Em Reais)")
                    
                    col_metrics = st.columns(4)
                    df_comp = resultados["df_comparacao"]
                    
                    for index, row in df_comp.iterrows():
                        with col_metrics[index]:
                            st.metric(
                                label=row["Categoria"],
                                value=f"{row['Pct Atual']*100:.1f}%",
                                delta=f"Meta: {row['Meta Pct']*100:.0f}%",
                                delta_color="off"
                            )
                    
                    st.divider()
                    st.subheader("🎯 Plano de Ação")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        compras = resultados["df_compras"]
                        if not compras.empty:
                            st.success("### ✅ Comprar")
                            st.table(compras[["Categoria", "Diferença (R$)"]].style.format({"Diferença (R$)": "R$ {:,.2f}"}))
                        else:
                            st.info("Nada para comprar.")
                            
                    with c2:
                        vendas = resultados["df_vendas"]
                        if not vendas.empty:
                            st.error("### 🔻 Vender")
                            vendas_view = vendas.copy()
                            vendas_view["Diferença (R$)"] = vendas_view["Diferença (R$)"].abs()
                            st.table(vendas_view[["Categoria", "Diferença (R$)"]].style.format({"Diferença (R$)": "R$ {:,.2f}"}))
                        else:
                            st.success("Nada para vender.")

                    if resultados["valor_outros"] > 0:
                        st.warning(f"⚠️ Ativos não classificados somam R$ {resultados['valor_outros']:,.2f}.")

with tab_metas:
    st.header("🎯 Painel de Metas")
    
    col_form, col_view = st.columns([1, 2])
    with col_form:
        st.subheader("Nova Meta")
        tipo_meta = st.selectbox(
            "Tipo de Meta",
            ["Patrimônio Total", "Total em Categoria", "Renda Passiva (Total)"]
        )
        
        filtro_input = ""
        if tipo_meta == "Total em Categoria":
            filtro_input = st.selectbox(
                "Qual Categoria?", 
                ["Renda Fixa", "Stocks", "ETF Internacional", "Criptomoedas"]
            )
        with st.form("form_meta"):
            valor_alvo = st.number_input("Valor Alvo (R$)", min_value=0.0, step=1000.0)
            descricao = st.text_input("Nome da Meta (Ex: Aposentadoria, Carro)")
            data_limite = st.date_input("Prazo (Opcional)")
            
            submitted = st.form_submit_button("Salvar Meta 💾")
            
            if submitted:
                if valor_alvo > 0:
                    criar_meta(tipo_meta, filtro_input, valor_alvo, str(data_limite), descricao)
                    st.success("Meta criada!")
                    st.rerun()
                else:
                    st.error("O valor deve ser maior que zero.")
    with col_view:
        st.subheader("Acompanhamento")
        metas_db = listar_metas()
        if not metas_db:
            st.info("Nenhuma meta cadastrada. Use o formulário ao lado.")
        else:
            dados_brutos = consultar_extrato()
            if dados_brutos:
                colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", "Corretora", "Categoria", "Moeda", "Cambio", "Obs"]
                if len(dados_brutos[0]) != 12: colunas_db = ["ID", "Data", "Ativo", "Tipo", "Qtd",
                                                              "Preço", "Total", "Corretora", "Moeda", "Cambio", "Obs"]
                df_metas = pd.DataFrame(dados_brutos, columns=colunas_db)
                lista_progresso = calcular_progresso_metas(df_metas, metas_db)
                
                for item in lista_progresso:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"### {item['titulo']}")
                        if c2.button("🗑️", key=f"del_{item['id']}", help="Excluir Meta"):
                            excluir_meta(item['id'])
                            st.rerun()

                        st.progress(item['pct'], text=f"{item['pct']*100:.1f}% Concluído")

                        m1, m2, m3 = st.columns(3)
                        m1.caption("Atual")
                        m1.markdown(f"R$ {item['valor_atual']:,.2f}")
                        
                        m2.caption("Objetivo")
                        m2.markdown(f"R$ {item['valor_alvo']:,.2f}")
                        
                        m3.caption("Falta")
                        m3.markdown(f"**R$ {item['falta']:,.2f}**")
                        
                        if item['pct'] >= 1.0:
                            st.success("🎉 PARABÉNS! META ATINGIDA!")
            else:
                st.warning("Cadastre transações no sistema para ver o progresso.")