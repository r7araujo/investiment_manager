import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'db', 'maindata.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE transacoes ADD COLUMN categoria TEXT DEFAULT 'Outros'")
    print("✅ Coluna 'categoria' adicionada com sucesso!")
except sqlite3.OperationalError:
    print("⚠️ A coluna 'categoria' provavelmente já existe.")

conn.commit()
conn.close()