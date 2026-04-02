import os
import socket
import re
import paramiko

# --- CONFIGURAÇÃO ---
ETHO_USER = "ethoscope"
ETHO_PASS = "ethoscope"


def convert_to_hostname(etho_name):
    """
    Transforma 'ETHOSCOPE_101' em 'ETHOSCOPE101'.
    Remove underscores e espaços.
    """
    # Remove o underscore e garante que está em maiúsculas
    hostname = etho_name.replace("_", "").replace(" ", "").upper()
    return hostname


def get_ip_from_hostname(hostname):
    """Resolve o IP do hostname localmente via mDNS."""
    clean_host = hostname.split('.')[0]
    full_host = f"{clean_host}.local"

    print(f"[*] A procurar o dispositivo na rede: {full_host}...")
    try:
        return socket.gethostbyname(full_host)
    except socket.gaierror:
        return None


def main():
    # 1. Input do utilizador (Agora pede o formato da pasta)
    etho_folder_name = input("Digite o nome do Ethoscope (ex: ETHOSCOPE_101): ").strip()
    if not etho_folder_name:
        return

    # 2. Inverter para Hostname para ligar à rede
    target_hostname = convert_to_hostname(etho_folder_name)
    etho_ip = get_ip_from_hostname(target_hostname)

    if not etho_ip:
        print(f"❌ Erro: Não foi possível encontrar o IP para o hostname '{target_hostname}'.")
        print("Dica: Verifica se o dispositivo está ligado e na mesma rede Wi-Fi.")
        return

    # 3. Conexão SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"[OK] Dispositivo encontrado em {etho_ip}")
        print(f"[*] A iniciar ligação SSH...")
        client.connect(etho_ip, username=ETHO_USER, password=ETHO_PASS, timeout=15)

        # 4. Identificar o ID único (Pasta Hexadecimal) automaticamente
        stdin, stdout, stderr = client.exec_command("ls -1 /ethoscope_data/results/")
        res_folders = stdout.read().decode().splitlines()

        # Filtra pastas longas (IDs hexadecimais)
        ids = [f for f in res_folders if len(f) > 10]

        if not ids:
            print("❌ Erro: Nenhuma pasta de ID encontrada em /ethoscope_data/results/")
            return

        etho_id = ids[0]
        print(f"[OK] ID do dispositivo detetado: {etho_id}")

        # 5. Listar Pastas de Experiências (Caminho com o nome original ETHOSCOPE_XXX)
        target_dir = f"/ethoscope_data/results/{etho_id}/{etho_folder_name}/"
        print(f"[*] A aceder a: {target_dir}")

        stdin, stdout, stderr = client.exec_command(f"ls -1 {target_dir}")
        folders = stdout.read().decode().splitlines()

        if not folders:
            print(f"[-] Nenhuma pasta de dados encontrada em {etho_folder_name}.")
            print(f"Dica: Verifica se o nome '{etho_folder_name}' está correto (maiúsculas/minúsculas importam).")
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

        # 6. Download via SFTP
        file_name = f"{folder}_{etho_id}.db"
        remote_path = f"{target_dir}{folder}/{file_name}"

        print(f"[*] A descarregar base de dados: {file_name}...")
        sftp = client.open_sftp()
        sftp.get(remote_path, file_name)
        sftp.close()

        print(f"\n✅ Download concluído!")
        print(f"📍 Localização: {os.path.abspath(file_name)}")

    except Exception as e:
        print(f"\n❌ Erro de ligação/transferência: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()