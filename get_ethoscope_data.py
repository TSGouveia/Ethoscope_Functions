import os
import paramiko
import sys
import time

# --- CONFIGURAÇÃO ---
ETHO_USER = "ethoscope"
ETHO_PASS = "ethoscope"


def progress_bar(transferred, total):
    percentage = (transferred / total) * 100
    transferred_mb = transferred / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    bar_length = 30
    filled_length = int(bar_length * transferred // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f"\r[*] Download: |{bar}| {percentage:.1f}% ({transferred_mb:.2f}/{total_mb:.2f} MB)")
    sys.stdout.flush()


def main():
    etho_folder_name = input("Nome da pasta (ex: ETHOSCOPE_101): ").strip()
    etho_ip = input("IP do Ethoscope: ").strip()

    if not etho_ip or not etho_folder_name: return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"[*] A ligar a {etho_ip}...")
        client.connect(etho_ip, username=ETHO_USER, password=ETHO_PASS, timeout=15)

        # 1. Detetar ID
        _, stdout, _ = client.exec_command("ls -1 /ethoscope_data/results/")
        ids = [f for f in stdout.read().decode().splitlines() if len(f) > 10]
        if not ids: return
        etho_id = ids[0]

        # 2. Listar experiências
        target_dir = f"/ethoscope_data/results/{etho_id}/{etho_folder_name}/"
        _, stdout, _ = client.exec_command(f"ls -1 {target_dir}")
        folders = stdout.read().decode().splitlines()

        if not folders:
            print("[-] Pasta não encontrada.")
            return

        for i, f in enumerate(folders):
            print(f"[{i + 1}] {f}")

        esc = int(input("\nEscolha o número: "))
        folder = folders[esc - 1]

        db_name = f"{folder}_{etho_id}.db"
        remote_path = f"{target_dir}{folder}/{db_name}"
        temp_path = f"/tmp/{db_name}"

        # --- OPERAÇÃO RESILIENTE ---
        print(f"[*] A preparar cópia segura (forçando escrita em disco)...")
        # cp + sync garante que o ficheiro é fechado e escrito corretamente no SD
        client.exec_command(f"cp {remote_path} {temp_path} && sync")
        time.sleep(2)  # Pausa técnica para o SO processar o ficheiro

        # Verificar integridade básica no próprio Ethoscope antes de baixar
        print(f"[*] A validar integridade no dispositivo...")
        stdin, stdout, stderr = client.exec_command(f"sqlite3 {temp_path} 'PRAGMA integrity_check;'")
        status = stdout.read().decode().strip()

        if "ok" not in status.lower():
            print("⚠️ Aviso: A base de dados original parece ter erros. Vou tentar baixar mesmo assim.")
        else:
            print("[OK] Integridade confirmada no dispositivo.")

        # 3. Obter tamanho para verificação final
        sftp = client.open_sftp()
        remote_size = sftp.stat(temp_path).st_size

        # 4. Download
        sftp.get(temp_path, db_name, callback=progress_bar)
        sftp.close()
        print("\n")

        # 5. Verificação Final de Tamanho
        local_size = os.path.getsize(db_name)
        if local_size != remote_size:
            print(f"❌ Erro: Tamanho incompatível! (Local: {local_size} vs Remoto: {remote_size})")
        else:
            print(f"✅ Download verificado com sucesso!")

        # Limpeza
        client.exec_command(f"rm {temp_path}")
        print(f"📍 Local: {os.path.abspath(db_name)}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()