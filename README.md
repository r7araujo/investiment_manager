# 💰 Gerenciador de Investimentos

Uma aplicação web desenvolvida em **Python** e **Streamlit** para controle pessoal de carteira de investimentos. O sistema permite registrar aportes, vendas e proventos, calculando automaticamente o preço médio, lucro realizado e a evolução patrimonial ao longo do tempo.


![Status do Projeto](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)

## 🎯 Funcionalidades

### 📊 Dashboard Interativo
- **KPIs em Tempo Real:** Total Investido (Preço de Custo), Renda Passiva (Dividendos + Caixinhas) e Lucro Realizado (Vendas).
- **Gráfico de Evolução:** Visualização mensal de aportes (barras) e crescimento do patrimônio (linha).
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

### ⚠️ Configuração do Banco de Dados (Passo Obrigatório)
**Importante:** O arquivo de banco de dados (`maindata.db`) **não está incluído no repositório** para preservar a privacidade dos dados. Antes de rodar o projeto pela primeira vez, você deve inicializá-lo:

1. Certifique-se de estar na raiz do projeto.
2. Execute o script de criação (ele aplica as migrações na ordem correta):
   ```bash
   python scripts/creator_db.py
Isso criará o arquivo maindata.db dentro da pasta db/.
🏃‍♂️ Iniciando a Aplicação

Você pode executar o projeto de duas maneiras: usando Docker (ambiente isolado e automático) ou Manualmente (Python local).
Opção 1: Usando Docker (Recomendado)

Pré-requisito: Ter o Docker Desktop instalado.

   Clone o repositório e entre na pasta:
   ```bash
   git clone [https://github.com/r7araujo/investiment-manager.git](https://github.com/r7araujo/investiment-manager.git)
   cd investiment-manager
   docker-compose up
3. Pronto! Acesse o navegador em: http://localhost:8501

Opção 2: Instalação Manual (Local)

Pré-requisito: Ter Python 3.10+ instalado.

1. Clone o repositório e entre na pasta:
   ```bash
   git clone [https://github.com/r7araujo/investiment-manager.git](https://github.com/r7araujo/investiment-manager.git)
   cd investiment-manager
2. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   pip install -r requirements.txt
3. Execute o Streamlit:
   ```bash
   streamlit run src/app.py