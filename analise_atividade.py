import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import glob

# CONFIGURAÇÃO
THRESHOLD_GAP_MINUTOS = 5  # O que é considerado um "buraco" nos dados (minutos)


def select_database_file():
    """Procura ficheiros .db no diretório atual e pede ao utilizador para escolher um."""
    db_files = glob.glob('*.db')

    if not db_files:
        print("❌ Nenhum ficheiro .db encontrado no diretório atual.")
        return None

    print("\nBases de dados disponíveis:")
    for i, file in enumerate(db_files):
        print(f"[{i + 1}] {file}")

    while True:
        try:
            choice = input(f"\nEscolha o número da base de dados (1-{len(db_files)}): ")
            index = int(choice)
            if 1 <= index <= len(db_files):
                return db_files[index - 1]
            else:
                print("⚠️ Escolha inválida. Tente novamente.")
        except ValueError:
            print("⚠️ Por favor, insira um número inteiro.")


def debug_presenca_absoluta():
    path = select_database_file()
    if not path:
        return

    print(f"\n[*] A analisar: {path}")
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # 1. Obter o Start Time da tabela METADATA (Epoch)
    start_time_epoch = 0.0
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='METADATA'")
    if cursor.fetchone():
        try:
            df_meta = pd.read_sql_query("SELECT * FROM METADATA", conn)
            start_time_epoch = float(df_meta[df_meta['field'] == 'date_time']['value'].iloc[0])
        except Exception as e:
            print(f"⚠️ Não foi possível extrair o tempo de início da METADATA: {e}")
    else:
        print("⚠️ Tabela METADATA não encontrada. A usar epoch 0.")

    # 2. Identificar tabelas de ROI
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ROI_%' AND name NOT LIKE '%MAP%'")
    tables = [t[0] for t in cursor.fetchall()]
    # Ordenar numericamente (ROI_1, ROI_2, ROI_10...)
    tables.sort(key=lambda x: int(''.join(filter(str.isdigit, x))) if any(char.isdigit() for char in x) else 0)

    # 3. Verificar IMG_SNAPSHOTS (case-insensitive)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name COLLATE NOCASE = 'img_snapshots'")
    snap_row = cursor.fetchone()
    has_snapshots = snap_row is not None
    snap_table_name = snap_row[0] if has_snapshots else None

    # Preparar labels do eixo Y
    y_labels = tables.copy()
    if has_snapshots:
        y_labels.append("IMG_SNAPSHOTS")

    fig, ax = plt.subplots(figsize=(12, 8))

    # Converter threshold de minutos para milissegundos
    gap_threshold_ms = THRESHOLD_GAP_MINUTOS * 60 * 1000

    print("[*] A processar intervalos e snapshots...")

    # Desenhar dados das ROIs
    for i, table in enumerate(tables):
        df = pd.read_sql_query(f"SELECT t FROM {table} ORDER BY t", conn)

        if df.empty:
            ax.text(0.01, i, f" {table} (EMPTY)", color='red', va='center', fontsize=9,
                    transform=ax.get_yaxis_transform())
            continue

        # Converter 't' relativo (ms) para datetime absoluto
        df['datetime'] = pd.to_datetime(start_time_epoch + (df['t'] / 1000.0), unit='s')

        # Detetar saltos (gaps)
        diffs = df['t'].diff()
        gap_indices = diffs[diffs > gap_threshold_ms].index.tolist()
        indices = [0] + gap_indices + [len(df)]

        # Desenhar segmentos contínuos
        for s, e in zip(indices[:-1], indices[1:]):
            segment_dt = df['datetime'].iloc[s:e]
            if not segment_dt.empty:
                ax.hlines(i, segment_dt.min(), segment_dt.max(), colors='blue', linewidth=5, alpha=0.7)

    # Desenhar snapshots, se existirem
    show_legend = False
    if has_snapshots:
        snapshot_idx = len(tables)
        df_snap = pd.read_sql_query(f"SELECT t FROM {snap_table_name} ORDER BY t", conn)

        if not df_snap.empty:
            df_snap['datetime'] = pd.to_datetime(start_time_epoch + (df_snap['t'] / 1000.0), unit='s')
            ax.scatter(df_snap['datetime'], [snapshot_idx] * len(df_snap),
                       color='green', marker='|', s=100, label='Snapshots', alpha=0.8)
            show_legend = True
        else:
            ax.text(0.01, snapshot_idx, " IMG_SNAPSHOTS (EMPTY)", color='red', va='center', fontsize=9,
                    transform=ax.get_yaxis_transform())

    # Formatação do Gráfico
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Absolute Time")
    ax.set_title(
        f"Interruption and Snapshot Analysis - {os.path.basename(path)}\n(White spaces = Gaps > {THRESHOLD_GAP_MINUTOS} min)")

    # Formatar eixo X para mostrar data e hora
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    fig.autofmt_xdate()  # Roda as datas para não se sobreporem

    ax.grid(True, axis='x', linestyle='--', alpha=0.3)

    # Adicionar legenda apenas se houver snapshots com dados
    if show_legend:
        ax.legend(loc='upper right')

    # Ajuste manual de margens para evitar erros de Tight Layout
    plt.subplots_adjust(left=0.15, bottom=0.15, right=0.95, top=0.9)

    output_img = "debug_interrupcoes_absolutas.png"

    try:
        # Forçar DPI como inteiro para evitar MatplotlibDeprecationWarning
        plt.savefig(output_img, dpi=int(200))
        print(f"✅ Gráfico guardado em: {os.path.abspath(output_img)}")
    except Exception as e:
        print(f"❌ Erro ao guardar imagem: {e}")

    plt.show()
    conn.close()


if __name__ == "__main__":
    debug_presenca_absoluta()