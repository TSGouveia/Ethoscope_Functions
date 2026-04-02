import os
import socket
import re
import paramiko

# --- CONFIGURAÇÃO ---
ETHO_USER = "ethoscope"
ETHO_PASS = "ethoscope"


def format_etho_name(hostname):
    """Transforma 'ETHOSCOPE101' em 'ETHOSCOPE_101'."""
    match = re.search(r"(\D+)(\d+)", hostname)
    if match:
        prefix = match.group(1).upper()
        number = match.group(2)
        return f"{prefix}_{number}"
    return hostname.upper()


def get_ip_from_hostname(hostname):
    """Resolve o IP do hostname localmente via mDNS."""
    clean_host = hostname.split('.')[0]
    full_host = f"{clean_host}.local"

    print(f"[*] A resolver endereço para {full_host}...")
    try:
        return socket.gethostbyname(full_host)
    except socket.gaierror:
        return None


def main():
    # 1. Input e Resolução
    raw_hostname = input("Digite o Hostname do Ethoscope (ex: ETHOSCOPE101): ").strip()
    if not raw_hostname: return

    etho_dynamic_name = format_etho_name(raw_hostname)
    etho_ip = get_ip_from_hostname(raw_hostname)

    if not etho_ip:
        print(f"❌ Erro: Não foi possível encontrar o IP para '{raw_hostname}'.")
        return

    # 2. Conexão SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"[OK] IP: {etho_ip}")
        print(f"[*] A ligar a {etho_ip}...")
        client.connect(etho_ip, username=ETHO_USER, password=ETHO_PASS, timeout=15)

        # 3. Identificar o ID automaticamente (Pasta Hexadecimal)
        stdin, stdout, stderr = client.exec_command("ls -1 /ethoscope_data/results/")
        res_folders = stdout.read().decode().splitlines()
        ids = [f for f in res_folders if len(f) > 10]

        if not ids:
            print("❌ Erro: Nenhuma pasta de ID encontrada.")
            return

        etho_id = ids[0]
        print(f"[OK] ID detetado: {etho_id}")

        # 4. Listar Pastas de Experiências
        target_dir = f"/ethoscope_data/results/{etho_id}/{etho_dynamic_name}/"
        print(f"[*] A procurar experiências em: {target_dir}")

        stdin, stdout, stderr = client.exec_command(f"ls -1 {target_dir}")
        folders = stdout.read().decode().splitlines()

        if not folders:
            print(f"[-] Nenhuma pasta encontrada em {etho_dynamic_name}.")
            return

        for i, f in enumerate(folders):
            print(f"[{i + 1}] {f}")

        try:
            esc = int(input("\nEscolha o número da pasta: "))
            folder = folders[esc - 1]
        except (ValueError, IndexError):
            print("❌ Seleção inválida.")
            return

        # 5. Download via SFTP
        file_name = f"{folder}_{etho_id}.db"
        remote_path = f"{target_dir}{folder}/{file_name}"

        print(f"[*] A baixar: {file_name}...")
        sftp = client.open_sftp()
        sftp.get(remote_path, file_name)
        sftp.close()

        print(f"\n✅ Sucesso! Ficheiro: {os.path.abspath(file_name)}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()