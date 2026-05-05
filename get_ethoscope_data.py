import os
import paramiko
import sys

# --- CONFIGURAÇÃO ---
ETHO_USER = "ethoscope"
ETHO_PASS = "ethoscope"


def progress_bar(transferred, total):
    """Função de callback para mostrar o progresso no terminal."""
    percentage = (transferred / total) * 100
    # Converter para MB para ser mais legível
    transferred_mb = transferred / (1024 * 1024)
    total_mb = total / (1024 * 1024)

    # Desenhar uma barra simples [#####     ]
    bar_length = 30
    filled_length = int(bar_length * transferred // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    # Imprimir na mesma linha (\r)
    sys.stdout.write(f"\r[*] Progresso: |{bar}| {percentage:.1f}% ({transferred_mb:.2f} / {total_mb:.2f} MB)")
    sys.stdout.flush()


def main():
    etho_folder_name = input("Digite o nome da pasta (ex: ETHOSCOPE_101): ").strip()
    etho_ip = input("Digite o IP do Ethoscope: ").strip()

    if not etho_ip or not etho_folder_name:
        print("❌ Erro: Dados incompletos.")
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"[*] A ligar a {etho_ip}...")
        client.connect(etho_ip, username=ETHO_USER, password=ETHO_PASS, timeout=15)

        # 1. Detetar ID
        stdin, stdout, stderr = client.exec_command("ls -1 /ethoscope_data/results/")
        ids = [f for f in stdout.read().decode().splitlines() if len(f) > 10]
        if not ids: return
        etho_id = ids[0]

        # 2. Listar experiências
        target_dir = f"/ethoscope_data/results/{etho_id}/{etho_folder_name}/"
        stdin, stdout, stderr = client.exec_command(f"ls -1 {target_dir}")
        folders = stdout.read().decode().splitlines()

        if not folders:
            print(f"[-] Nenhuma pasta encontrada.")
            return

        print("\nExpedições encontradas:")
        for i, f in enumerate(folders):
            print(f"[{i + 1}] {f}")

        esc = int(input("\nEscolha o número: "))
        folder = folders[esc - 1]

        db_name = f"{folder}_{etho_id}.db"
        remote_path = f"{target_dir}{folder}/{db_name}"
        temp_path = f"/tmp/{db_name}"

        # 3. Cópia interna no dispositivo
        print(f"[*] A preparar cópia de segurança no Ethoscope...")
        client.exec_command(f"cp {remote_path} {temp_path}")

        # 4. Download Informativo
        print(f"[*] A iniciar download de: {db_name}")
        sftp = client.open_sftp()

        # O segredo está aqui: passamos a função progress_bar como callback
        sftp.get(temp_path, db_name, callback=progress_bar)

        sftp.close()
        print("\n")  # Salto de linha após a barra de progresso

        # 5. Limpeza
        client.exec_command(f"rm {temp_path}")
        print(f"✅ Sucesso! Ficheiro: {os.path.abspath(db_name)}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()