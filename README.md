# 💰 Gerenciador de Investimentos

Uma aplicação web desenvolvida em **Python** e **Streamlit** para controle pessoal de carteira de investimentos. O sistema permite registrar aportes, vendas e proventos, calculando automaticamente o preço médio, lucro realizado e a evolução patrimonial ao longo do tempo.

![Status do Projeto](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)

## 🎯 Funcionalidades

### 📊 Dashboard Interativo
- **KPIs em Tempo Real:** Total Investido (Preço de Custo), Renda Passiva (Dividendos + Caixinhas) e Lucro Realizado (Vendas).
- **Gráfico de Evolução:** Visualização mensal de aportes (barras) e crescimento do patrimônio (linha), com projeção mínima de 12 meses.
- **Alocação de Ativos:** Gráficos de Pizza interativos divididos por **Renda Fixa** e **Renda Variável**, com legendas laterais e filtros dinâmicos.
- **Mini-Extrato:** Tabela filtrável na própria tela inicial para consulta rápida de posições.

### ⚙️ Gerenciamento de Transações
- Cadastro de operações: Compra, Venda, Dividendo, JCP, Bonificação.
- Suporte a diversas classes: Ações, FIIs, Tesouro Direto, CDBs (Caixinhas), Criptomoedas e Stocks.
- **Lógica Inteligente de Venda:** O sistema abate o custo proporcional baseando-se no Preço Médio, calculando o lucro/prejuízo real da operação.
- **Bonificações/Caixinhas:** Suporte para reinvestimento automático com custo zero (aumenta quantidade sem alterar custo de aquisição).

### 📑 Extrato Completo
- Histórico detalhado de todas as transações.
- Filtros por intervalo de datas e tipos de operação.

## 🛠️ Tecnologias Utilizadas

- **Python:** Linguagem principal.
- **Streamlit:** Framework para construção da interface web.
- **Pandas:** Manipulação e análise de dados (DataFrames).
- **Plotly:** Criação de gráficos interativos e responsivos.
- **SQLite:** Banco de dados local leve e eficiente.

## 🚀 Como Executar o Projeto

### Pré-requisitos
Certifique-se de ter o Python instalado. Recomenda-se usar um ambiente virtual (`venv`).

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/r7araujo/investiment-manager.git](https://github.com/r7araujo/investiment-manager.git)
   cd investiment-manager
   pip install -r requirements.txt
   streamlit run src/app.py