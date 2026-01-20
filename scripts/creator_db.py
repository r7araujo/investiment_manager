import subprocess
import sys
import os

def run_script(script_name):
    """
    Executa um script Python localizado na mesma pasta que este arquivo.
    """
    base_path = os.path.dirname(__file__)
    script_path = os.path.join(base_path, script_name)

    print(f"🔄 Executando {script_name}...")

    try:
        result = subprocess.run([sys.executable, script_path], check=True, text=True)
        print(f"✅ {script_name} concluído com sucesso!\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar {script_name}.")
        print(f"O processo parou para evitar inconsistências.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {script_path}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Iniciando configuração do Banco de Dados...\n")
    run_script("db_creator.py")
    run_script("db_mod1.py")
    print("🎉 Banco de dados configurado e atualizado com sucesso!")