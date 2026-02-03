import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from datetime import date
from constants import *
from database import *
from utils import *
# Cria os bancos de dados no maindata.db e consultando os dados
inicializar_tabela_transacoes()
inicializar_tabela_config()
inicializar_tabela_metas()
dados = consultar_extrato()

# Inicio do streamlit
st.set_page_config(page_title="Meus Investimentos", layout="wide")
st.title("💰 Gerenciador de Investimentos")

tab_dash, tab_extrato, tab_registrar, tab_atual, tab_rebal, tab_metas = st.tabs([
    "📊 Dashboard", "📑 Extrato", "⚙️ Registrador", "📈 Atualidades", "⚖️ Rebalanceador", "🎯 Metas"
    ])

with tab_dash:
    st.header("Visão Geral & Performance")    
    if not dados:
        st.info("Cadastre operações na aba 'Registrador' para ver os indicadores.")
    else:
        df = pd.DataFrame(dados, columns=COLUNAS_DB)
        df['Data'] = pd.to_datetime(df['Data'])
        carteira = calcular_carteira_atual(df)
        lucro_realizado = calcular_lucro_realizado(df)
        total_bonificacoes = calcular_total_bonificacoes(df)
        patrimonio_investido = sum(item['custo_total'] for item in carteira.values())
        proventos_caixa = df[df['Tipo'].isin(['Dividendo', 'JCP'])]['Total'].sum()
        renda_passiva_total = proventos_caixa + total_bonificacoes
        proventos_ano = calcular_proventos_ano_atual(df)
        dy_anual = (proventos_ano / patrimonio_investido * 100) if patrimonio_investido > 0 else 0.0

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Investido (Custo)", f"R$ {patrimonio_investido:,.2f}")
        with col2:
            st.metric("Renda Passiva Total", f"R$ {renda_passiva_total:,.2f}")
        with col3:
            st.metric("Lucro Realizado", f"R$ {lucro_realizado:,.2f}", 
                        delta=f"{lucro_realizado:,.2f}" if lucro_realizado != 0 else None)
        with col4:
            st.metric("Rendimento Anual (R$)", f"R$ {proventos_ano:,.2f}", help="Soma de Dividendos, JCP e Bonificações deste ano")
        with col5:
             st.metric("Yield on Cost Anual", f"{dy_anual:.2f}%", help="Rendimento Anual / Total Investido")
    
    st.divider()
    col_graf1, col_graf2 = st.columns([1, 2])

    with col_graf1:
        st.subheader("Alocação por Classe")
        
        df_pizza = calcular_alocacao_por_classe(df)
        
        if not df_pizza.empty:
            fig_pizza = px.pie(
                df_pizza, 
                values='Total', 
                names='Classe_Ativo', 
                hole=0.5,
                color_discrete_sequence=['#4222d7', '#f1ab4e']
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
                data_futura_minima = data_inicio + pd.DateOffset(months=12) # Garante pelo menos 12 meses de visão
                data_fim = max(data_hoje, data_futura_minima)
                
                date_range = pd.date_range(start=data_inicio, end=data_fim, freq='MS')
                
                # Listas para o gráfico
                eixo_datas, eixo_aportes, eixo_acumulado = calcular_evolucao_patrimonial(df_sorted, date_range)

                fig_evolucao = go.Figure()
                
                fig_evolucao.add_trace(go.Bar(
                    x=eixo_datas, 
                    y=eixo_aportes, 
                    name='Aporte Mensal',
                    marker_color='#114c0e'
                ))
                
                fig_evolucao.add_trace(go.Scatter(
                    x=eixo_datas, 
                    y=eixo_acumulado, 
                    name='Total Investido (Custo)',
                    mode='lines+markers',
                    line=dict(color='#447a37', width=3)
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
    df_posicao = gerar_tabela_alocacao(carteira, df)
    
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
            # cat_unicas = sorted(df_posicao['Categoria'].unique().tolist()) # Removido
            # Agora filtramos por CLASSE (Renda Fixa ou Variável)
            opcoes_filtro = ["Todos", "Renda Variável", "Renda Fixa"]
            filtro_tabela = st.selectbox("Filtrar Tabela:", opcoes_filtro)
            
            if filtro_tabela != "Todos":
                df_exibir = df_posicao[df_posicao['Classe'] == filtro_tabela]
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
    st.subheader("🧾 Mini Extrato - Posição Atual")
    if dados:
        if len(dados[0]) == len(COLUNAS_DB):
            df_transacoes = pd.DataFrame(dados, columns=COLUNAS_DB)
            df_mini_extrato = calcular_resumo_ativos(df_transacoes)
            
            if not df_mini_extrato.empty:
                st.dataframe(
                    df_mini_extrato,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Ativo": st.column_config.TextColumn("Ativo", width="small"),
                        "Quantidade": st.column_config.NumberColumn(
                            "Qtd", 
                            format="%.4f"
                        ),
                        "Preço Médio": st.column_config.NumberColumn(
                            "Preço Médio",
                            format="R$ %.2f"
                        ),
                        "Total Investido": st.column_config.NumberColumn(
                            "Total Investido",
                            format="R$ %.2f"
                        )
                    }
                )
                total_geral = df_mini_extrato["Total Investido"].sum()
                st.caption(f"**Patrimônio Total (Custo):** R$ {total_geral:,.2f}")
            else:
                st.info("Você não possui ativos em carteira no momento.")
        else:
            st.error("Erro na estrutura do banco de dados.")
    else:
        st.warning("Nenhuma transação registrada.")
    st.divider()
    st.header("Histórico de Transações")
    
    with st.expander("Filtros", expanded=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            data_inicial = st.date_input("Data Inicial", date(2023, 1, 1))
            data_final = st.date_input("Data Final", date.today())
        with col_f2:
            tipos_opcoes = TIPOS_OPCOES
            tipos_selecionados = st.multiselect("Filtrar Tipo", tipos_opcoes, default=tipos_opcoes)

    dados = consultar_extrato()
    
    if dados:
        df = pd.DataFrame(dados, columns=COLUNAS_DB)
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        mask_data = (df['Data'] >= data_inicial) & (df['Data'] <= data_final)
        mask_tipo = df['Tipo'].isin(tipos_selecionados)
        df_filtrado = df.loc[mask_data & mask_tipo]
        df_filtrado = df_filtrado.sort_values(by="Data", ascending=False)
        cols_visuais = ["Data", "Ativo", "Tipo", "Categoria", "Classe", "Qtd", "Preço", "Total", "Corretora", "Obs"]
        st.dataframe(
            df_filtrado[cols_visuais], 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Preço": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                "Total": st.column_config.NumberColumn("Total", format="R$ %.2f"),
                "Qtd": st.column_config.NumberColumn("Qtd", format="%.4f"),
                "Classe": st.column_config.TextColumn(
                    "Classe", 
                    help="Macro-categoria (Renda Fixa/Variável)",
                    validate="^(Renda Fixa|Renda Variável)$" 
                ),
            }
        )
    else:
        st.info("Nenhuma transação encontrada.")

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
                tipo = st.selectbox("Tipo", ['Compra', 'Venda', 'Dividendo', 'JCP', 'Taxa', 'Bonificacao', 'Cambio',
            'Aporte', 'Resgate', 'Reinvestimento'])
            
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
                    classe_definida = identificar_classe(categoria)
                    add_transacao(
                        data_op, ativo, tipo, qtd, preco, corretora, 
                        categoria, classe_definida, 
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
        
        ultimo_backup = ler_config("ultimo_backup")
        if ultimo_backup:
            st.caption(f"📅 Último backup: **{ultimo_backup}**")

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

with tab_atual:
    st.header("📈 Posição Atual (Online)")
    
    dados = consultar_extrato()
    if not dados:
        st.warning("Sem dados cadastrados.")
    else:
        df = pd.DataFrame(dados, columns=COLUNAS_DB)
        
        # Recalcula carteira
        carteira_atual = calcular_carteira_atual(df)
        
        if not carteira_atual:
            st.info("Carteira vazia.")
        else:
            with st.spinner("Buscando cotações online no Yahoo Finance..."):
                df_rentabilidade, resumo = gerar_painel_rentabilidade(carteira_atual, df)
            
            # --- Métricas de Cabeçalho ---
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Patrimônio Atual (Estimado)", f"R$ {resumo['valor_atual']:,.2f}")
            with col_m2:
                cor_delta = "normal"
                if resumo['lucro_total_rs'] > 0: cor_delta = "normal" # Verde padrao
                elif resumo['lucro_total_rs'] < 0: cor_delta = "inverse" # Vermelho
                
                st.metric(
                    "Lucro/Prej. Total (Não Realizado)", 
                    f"R$ {resumo['lucro_total_rs']:,.2f}",
                    delta=f"{resumo['lucro_total_pct']:.2f}%"
                )
            with col_m3:
                st.metric("Custo de Aquisição", f"R$ {resumo['custo_total']:,.2f}")
                
            st.divider()
            
            # --- Tabela Detalhada ---
            st.subheader("Rentabilidade por Ativo")
            
            if not df_rentabilidade.empty:
                st.dataframe(
                    df_rentabilidade,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Ativo": st.column_config.TextColumn("Ativo", width="small"),
                        "Qtd": st.column_config.NumberColumn("Qtd", format="%.4f"),
                        "PM": st.column_config.NumberColumn("Preço Médio", format="R$ %.2f"),
                        "Cotação Atual": st.column_config.NumberColumn("Cotação (Yahoo)", format="R$ %.2f"),
                        "Valor Atual": st.column_config.NumberColumn("Saldo Atual", format="R$ %.2f"),
                        "Lucro (R$)": st.column_config.NumberColumn("Lucro R$", format="R$ %.2f"),
                        "Var (%)": st.column_config.NumberColumn(
                            "Var %", 
                            format="%.2f %%"
                        ),
                        "Status": st.column_config.TextColumn("Status", width="small")
                    }
                )
                
                # Aviso se houver algum offline
                if "⚠️ Offline" in df_rentabilidade["Status"].values:
                    st.warning("⚠️ Alguns ativos não tiveram cotação encontrada e estão exibindo o preço de custo (PM) para não distorcer o total.")
                
                st.caption("*Cotações com delay de 15 min ou fechamento anterior. Fonte: Yahoo Finance.")
            else:
                st.info("Nenhum ativo elegível para cotação.")

with tab_rebal:
        st.header("⚖️ Rebalanceamento de Carteira")
        metas_usuario = ler_config("meta_alocacao")
        reserva_salva = float(ler_config("reserva_emergencia", 0.0))

        if not metas_usuario: 
            st.error("Erro: Metas não encontradas.")
            st.stop()
        with st.expander("⚙️ Configurar Metas e Reserva", expanded=False):
            with st.form("form_metas"):
                st.markdown("### 🛡️ Reserva de Emergência")
                nova_reserva = st.number_input("Valor da Reserva (R$)", min_value=0.0, value=reserva_salva, step=100.0, format="%.2f")
                
                st.divider()
                st.markdown("### 🎯 Metas de Alocação (%)")
                novas_metas = {}
                cols = st.columns(3)
                for i, (cat, val) in enumerate(metas_usuario.items()):
                    novas_metas[cat] = cols[i%3].number_input(f"% {cat}", 0.0, 100.0, float(val), 1.0)
                
                if st.form_submit_button("Salvar 💾"):
                    if abs(sum(novas_metas.values()) - 100.0) > 0.1:
                        st.error("A soma deve ser 100%.")
                    else:
                        salvar_config("meta_alocacao", novas_metas)
                        salvar_config("reserva_emergencia", nova_reserva)
                        st.success("Salvo!")
                        time.sleep(1)
                        st.rerun()

        st.divider()

        # Inputs iniciais
        c1, c2 = st.columns(2)
        aporte = c1.number_input("Aporte (R$)", 0.0, step=100.0)
        dolar = c2.number_input("Dólar (R$)", 5.50, step=0.01)

        # Processamento de dados
        dados = consultar_extrato()
        
        if dados:
            df_raw = pd.DataFrame(dados, columns=COLUNAS_DB)
            df_carteira = calcular_resumo_ativos(df_raw)
            
            if not df_carteira.empty:
                df_completo = unificar_dados_com_categorias(df_carteira, df_raw)
                df_editado = preparar_dados_editor(df_completo)
                st.markdown("### 1. Preencha os Preços")
                df_final = st.data_editor(
                    df_editado,
                    column_config={
                        "Preço Hoje": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f", required=True),
                        "Qtd Atual": st.column_config.NumberColumn(disabled=True),
                        "Classificação": st.column_config.TextColumn(disabled=True),
                        "Em Dólar?": st.column_config.CheckboxColumn(disabled=False)
                    },
                    hide_index=True,
                    use_container_width=True
                )
                st.divider()
                
                # --- Contador de Rebalanceamento ---
                ult_rebal = ler_config("ultimo_rebalanceamento")
                if ult_rebal:
                    try:
                        dt_ult = datetime.strptime(ult_rebal, "%Y-%m-%d").date()
                        hoje = date.today()
                        diferenca = hoje - dt_ult
                        meses = diferenca.days // 30
                        dias = diferenca.days % 30
                        st.info(f"📅 Último rebalanceamento realizado há **{meses} meses e {dias} dias** ({dt_ult.strftime('%d/%m/%Y')}).")
                    except:
                        st.caption("Data de rebalanceamento inválida.")

                c_reb1, c_reb2 = st.columns([1, 2])
                with c_reb1:
                    if st.button("✅ Marcar como Realizado", help="Salva a data de hoje como último rebalanceamento"):
                        salvar_config("ultimo_rebalanceamento", str(date.today()))
                        st.success("Data atualizada!")
                        time.sleep(1)
                        st.rerun()
                # -----------------------------------

                if st.button("Calcular Rebalanceamento 🚀", type="primary"):
                    res = calcular_rebalanceamento(df_final, aporte, dolar, metas_usuario, reserva_salva)
                    
                    st.subheader("🛒 Compras Indicadas")
                    if not res['df_compras'].empty:
                        st.dataframe(
                            res['df_compras'][["Categoria", "Diferença (R$)", "Saldo Atual (R$)", "Meta (R$)"]],
                            use_container_width=True, hide_index=True,
                            column_config={"Diferença (R$)": st.column_config.NumberColumn("Falta Comprar", format="R$ %.2f")}
                        )
                    else:
                        st.success("Nada a comprar por enquanto.")
                    
                    if not res['df_vendas'].empty:
                        with st.expander("⚠️ Vendas Indicadas"):
                            st.dataframe(res['df_vendas'][["Categoria", "Diferença (R$)"]], use_container_width=True)

                    st.markdown("---")
                    with st.expander("📊 Detalhes do Cálculo"):
                        st.dataframe(res['df_comparacao'], use_container_width=True, hide_index=True)
                        st.info(f"Patrimônio (Sem Reserva): R$ {res['patrimonio_atual']:,.2f}")
            else:
                st.info("Carteira vazia.")
        else:
            st.warning("Sem dados no banco.")

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
                df_metas = pd.DataFrame(dados_brutos, columns=COLUNAS_DB)
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