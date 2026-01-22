import sqlite3, os, json
from datetime import datetime
from constants import *

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_DB = os.path.join(DIRETORIO_ATUAL, '..', 'db', 'maindata.db')


# Aqui estão as funções que mexem com o banco de dados

# Funções que gerenciam o maindata.db

def conectar():
    """Conecta ao banco de dados e retorna a conexão."""
    return sqlite3.connect(CAMINHO_DB)

def inicializar_tabela_transacoes():
    """Cria a tabela de transações se ela não existir."""
    conn = conectar()
    cursor = conn.cursor()
    
    sql_criar_tabela = """
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        ativo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        quantidade REAL,
        preco_unitario REAL,
        valor_total REAL NOT NULL,
        corretora TEXT NOT NULL,
        moeda TEXT DEFAULT 'BRL',
        taxa_cambio REAL DEFAULT 1.0,
        observacao TEXT,
        categoria TEXT DEFAULT 'Outros',
        
        CHECK(tipo IN (
            'Compra', 'Venda', 'Dividendo', 'JCP', 'Taxa', 'Bonificacao', 'Cambio',
            'Aporte', 'Resgate', 'Reinvestimento'
        ))
    );
    """
    
    cursor.execute(sql_criar_tabela)
    conn.commit()
    conn.close()

def add_transacao(data, ativo, tipo, quantidade, preco, corretora, categoria, moeda='BRL', cambio=1.0, obs=''):
    conn = conectar()
    cursor = conn.cursor()
    
    qtd_final = quantidade if quantidade else 1
    valor_total = preco * qtd_final

    sql = """
    INSERT INTO transacoes 
    (data, ativo, tipo, quantidade, preco_unitario, valor_total, corretora, categoria, moeda, taxa_cambio, observacao)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    valores = (data, ativo.upper(), tipo, quantidade, preco, valor_total, corretora, categoria, moeda, cambio, obs)    
    try:
        cursor.execute(sql, valores)
        conn.commit()
        print(f"✅ Transação de {ativo} adicionada com sucesso!")
    except sqlite3.Error as e:
        print(f"❌ Erro ao inserir: {e}")
    finally:
        conn.close()

def del_transacao(id_transacao):
    """
    Remove uma transação baseada no ID.
    Isso é essencial para corrigir erros de lançamento.
    """
    conn = conectar()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM transacoes WHERE id = ?", (id_transacao,))
        conn.commit()
        print(f"✅ Transação ID {id_transacao} removida.")
    except sqlite3.Error as e:
        print(f"❌ Erro ao remover: {e}")
    finally:
        conn.close()

def consultar_extrato():
    """
    Retorna TODAS as transações ordenadas por data.
    """
    conn = conectar()
    cursor = conn.cursor()
    sql = """
    SELECT 
        id, 
        data, 
        ativo, 
        tipo, 
        quantidade, 
        preco_unitario, 
        valor_total, 
        corretora, 
        categoria, 
        moeda, 
        taxa_cambio, 
        observacao
    FROM transacoes 
    ORDER BY data DESC
    """
    
    try:
        cursor.execute(sql)
        resultado = cursor.fetchall()
        return resultado
    except sqlite3.Error as e:
        print(f"Erro ao consultar: {e}")
        return []
    finally:
        conn.close()

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

# Funções para modificar variáveis

def inicializar_tabela_config():
    """Cria tabela e insere valores default se estiver vazia."""
    conn = conectar()
    cursor = conn.cursor()
    
    # 1. Cria a tabela
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config (
        chave TEXT PRIMARY KEY,
        valor TEXT
    )
    """)
    
    # 2. SEED DATA: Verifica se já existem metas. Se não, insere as padrão.
    cursor.execute("SELECT chave FROM config WHERE chave = 'meta_alocacao'")
    existe = cursor.fetchone()
    
    if not existe:
        print("Configuração inicial não encontrada. Criando metas padrão no banco...")
        # Converte o dict para JSON (Texto)
        valor_json = json.dumps(METAS_PADRAO)
        cursor.execute("INSERT INTO config (chave, valor) VALUES (?, ?)", ('meta_alocacao', valor_json))
        conn.commit()
        
    conn.close()
    print("Tabela 'config' verificada com sucesso.")
    
def salvar_config(chave, valor):
    """
    Salva uma configuração. 
    Se o valor for lista/dicionário, converte para texto (JSON) automaticamente.
    """
    conn = conectar()
    cursor = conn.cursor()

    if isinstance(valor, (dict, list)):
        valor = json.dumps(valor)
    cursor.execute("""
    INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)
    """, (chave, str(valor)))
    
    conn.commit()
    conn.close()

def ler_config(chave, valor_padrao=None):
    """
    Lê uma configuração. Tenta converter de volta para JSON se parecer um.
    """
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config WHERE chave = ?", (chave,))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        valor_str = resultado[0]
        try:
            return json.loads(valor_str)
        except:
            return valor_str 
            
    return valor_padrao

# Funções de meta

def inicializar_tabela_metas():
    """Cria a tabela de metas se não existir."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL,          -- Ex: 'Patrimônio Total', 'Categoria', 'Renda Passiva'
        filtro TEXT,                 -- Ex: 'Renda Fixa', 'FII', ou vazio se for geral
        valor_alvo REAL NOT NULL,
        data_limite TEXT,            -- Opcional
        descricao TEXT
    )
    """)
    conn.commit()
    conn.close()

def criar_meta(tipo, filtro, valor_alvo, data_limite, descricao):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO metas (tipo, filtro, valor_alvo, data_limite, descricao)
    VALUES (?, ?, ?, ?, ?)
    """, (tipo, filtro, valor_alvo, data_limite, descricao))
    conn.commit()
    conn.close()

def listar_metas():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM metas")
    dados = cursor.fetchall()
    conn.close()
    return dados

def excluir_meta(id_meta):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM metas WHERE id = ?", (id_meta,))
    conn.commit()
    conn.close()
