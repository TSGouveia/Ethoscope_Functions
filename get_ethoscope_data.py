import os
import paramiko

# --- CONFIGURAÇÃO ---
ETHO_USER = "ethoscope"
ETHO_PASS = "ethoscope"

def main():
    # 1. Inputs do utilizador
    # O IP é usado para a ligação SSH
    etho_folder_name = input("Digite o nome da pasta (ex: ETHOSCOPE_101): ").strip()
    etho_ip = input("Digite o IP do Ethoscope (ex: 192.168.1.50): ").strip()
    # O Nome é usado para encontrar o caminho da pasta de resultados


    if not etho_ip or not etho_folder_name:
        print("❌ Erro: O IP e o Nome da pasta são obrigatórios.")
        return

    # 2. Conexão SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"[*] A iniciar ligação SSH para {etho_ip}...")
        client.connect(etho_ip, username=ETHO_USER, password=ETHO_PASS, timeout=15)
        print(f"[OK] Ligado com sucesso!")

        # 3. Identificar o ID único (Pasta Hexadecimal) automaticamente
        # Listamos o conteúdo de /ethoscope_data/results/ para encontrar o ID da máquina
        stdin, stdout, stderr = client.exec_command("ls -1 /ethoscope_data/results/")
        res_folders = stdout.read().decode().splitlines()

        # Filtra pastas longas (os IDs hexadecimais do Ethoscope costumam ser longos)
        ids = [f for f in res_folders if len(f) > 10]

        if not ids:
            print("❌ Erro: Nenhuma pasta de ID hexadecimal encontrada em /ethoscope_data/results/")
            return

        etho_id = ids[0]
        print(f"[OK] ID do dispositivo detetado no sistema: {etho_id}")

        # 4. Listar Pastas de Experiências
        # O caminho usa o ID detetado + o NOME que escreveste no início
        target_dir = f"/ethoscope_data/results/{etho_id}/{etho_folder_name}/"
        print(f"[*] A aceder a: {target_dir}")

        stdin, stdout, stderr = client.exec_command(f"ls -1 {target_dir}")
        folders = stdout.read().decode().splitlines()

        if not folders:
            print(f"[-] Nenhuma pasta de dados encontrada para '{etho_folder_name}'.")
            print(f"Dica: Verifica se o nome está exatamente igual ao que aparece no dispositivo.")
            return

        print("\nExpedições encontradas:")
        for i, f in enumerate(folders):
            print(f"[{i + 1}] {f}")

        try:
            esc = int(input("\nEscolha o número da pasta para baixar: "))
            folder = folders[esc - 1]
        except (ValueError, IndexError):
            print("❌ Seleção inválida.")
            return

        # 5. Download via SFTP
        # O ficheiro .db segue o padrão: nome-da-pasta_ID-da-maquina.db
        file_name = f"{folder}_{etho_id}.db"
        remote_path = f"{target_dir}{folder}/{file_name}"

        print(f"[*] A descarregar: {file_name}...")
        sftp = client.open_sftp()
        sftp.get(remote_path, file_name)
        sftp.close()

        print(f"\n✅ Download concluído com sucesso!")
        print(f"📍 Localização: {os.path.abspath(file_name)}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()