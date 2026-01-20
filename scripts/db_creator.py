import sqlite3
import os

diretorio_script = os.path.dirname(os.path.abspath(__file__))
caminho_banco = os.path.join(diretorio_script, '..', 'db', 'maindata.db')
os.makedirs(os.path.dirname(caminho_banco), exist_ok=True)

print(f"Criando/Conectando ao banco de dados em: {caminho_banco}")

conn = sqlite3.connect(caminho_banco)
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
    
    CHECK(tipo IN ('Compra', 'Venda', 'Dividendo', 'JCP', 'Taxa', 'Bonificacao', 'Cambio'))
);
"""

cursor.execute(sql_criar_tabela)

conn.commit()
conn.close()

print("Sucesso! O arquivo 'maindata.db' foi atualizado na pasta 'db'.")