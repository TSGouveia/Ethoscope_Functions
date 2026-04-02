import os
import subprocess
import sys


def main():
    try:
        if os.path.exists(".git"):
            print("🔄 A verificar atualizações no Git...")
            subprocess.run(["git", "pull"], check=True)

            if os.path.exists("requirements.txt"):
                print("📦 A instalar/atualizar dependências...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Tudo atualizado!")
        else:
            print("⚠️ Erro: Pasta .git não encontrada. O auto-update só funciona dentro de um repositório git.")
    except Exception as e:
        print(f"❌ Erro na atualização: {e}")


if __name__ == "__main__":
    main()