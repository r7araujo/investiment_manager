# Metas padrao, antes do usuario alterar
METAS_PADRAO = {
    "Renda Fixa": 30.0,
    "Ações": 20.0,
    "FIIs": 20.0,
    "Stocks": 15.0,
    "ETF Internacional": 10.0,
    "Criptomoedas": 5.0
}

# Colunas do maindata.db > transacoes
COLUNAS_DB = ["ID", "Data", "Ativo", "Tipo", "Qtd", "Preço", "Total", 
    "Corretora", "Categoria", "Moeda", "Cambio", "Obs", "Classe"]

# Mapeamento de Macro-Classes para Categorias Específicas
MAPA_CLASSES = {
    "Renda Fixa": ["Tesouro Direto", "CDB", "LCI/LCA", "Debêntures", "Caixinha"],
    "Renda Variável": ["Ações", "FIIs", "Stocks", "REITs", "ETF", "Criptomoedas", "BDR"]
}
# Gera a lista plana automaticamente baseada no mapa acima
LISTA_CATEGORIAS = [item for sublist in MAPA_CLASSES.values() for item in sublist] + ["Outros"]
