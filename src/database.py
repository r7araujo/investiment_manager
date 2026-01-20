import sqlite3, os
from datetime import datetime

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
CAMINHO_DB = os.path.join(DIRETORIO_ATUAL, '..', 'db', 'maindata.db')

def conectar():
    """Conecta ao banco de dados e retorna a conexão."""
    return sqlite3.connect(CAMINHO_DB)

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

