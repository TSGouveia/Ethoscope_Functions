import os
import paramiko

# --- CONFIGURAÇÃO ---
ETHO_USER = "ethoscope"
ETHO_PASS = "ethoscope"


def main():
    # 1. Inputs do utilizador
    etho_folder_name = input("Digite o nome do Ethoscope (ex: ETHOSCOPE_101): ").strip()
    etho_ip = input("Digite o IP do Ethoscope: ").strip()

    if not etho_ip or not etho_folder_name:
        print("❌ Erro: IP e Nome são obrigatórios.")
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"[*] A ligar a {etho_ip}...")
        client.connect(etho_ip, username=ETHO_USER, password=ETHO_PASS, timeout=15)

        # 2. Detetar o ID Único (Hexadecimal)
        stdin, stdout, stderr = client.exec_command("ls -1 /ethoscope_data/results/")
        ids = [f for f in stdout.read().decode().splitlines() if len(f) > 10]

        if not ids:
            print("❌ Erro: ID não encontrado em /ethoscope_data/results/")
            return
        etho_id = ids[0]

        # 3. Listar experiências
        target_dir = f"/ethoscope_data/results/{etho_id}/{etho_folder_name}/"
        stdin, stdout, stderr = client.exec_command(f"ls -1 {target_dir}")
        folders = stdout.read().decode().splitlines()

        if not folders:
            print(f"[-] Nenhuma pasta encontrada em {target_dir}")
            return

        print("\nExpedições encontradas:")
        for i, f in enumerate(folders):
            print(f"[{i + 1}] {f}")

        esc = int(input("\nEscolha o número: "))
        folder = folders[esc - 1]

        # 4. Preparar caminhos
        db_name = f"{folder}_{etho_id}.db"
        remote_path = f"{target_dir}{folder}/{db_name}"
        temp_path = f"/tmp/{db_name}"  # Pasta temporária no Linux (RAM ou SD rápido)

        # --- PASSO CRÍTICO: COPIAR ANTES DE BAIXAR ---
        print(f"[*] A criar cópia temporária no Ethoscope...")
        # cp [origem] [destino]
        client.exec_command(f"cp {remote_path} {temp_path}")

        # 5. Download via SFTP
        print(f"[*] A descarregar: {db_name}...")
        sftp = client.open_sftp()
        sftp.get(temp_path, db_name)
        sftp.close()

        # 6. Limpeza
        print(f"[*] A remover ficheiro temporário do Ethoscope...")
        client.exec_command(f"rm {temp_path}")

        print(f"\n✅ Concluído! Ficheiro guardado em: {os.path.abspath(db_name)}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()