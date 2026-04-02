import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import glob

# CONFIGURATION
THRESHOLD_GAP_MINUTOS = 5  # Define what is considered a gap (in minutes)


def select_database_file():
    """Searches for .db files in the current directory and asks the user to choose one."""
    db_files = glob.glob('*.db')

    if not db_files:
        print("No .db files found in the current directory.")
        return None

    print("Available database files:")
    for i, file in enumerate(db_files):
        # Using 1-based indexing for the display
        print(f"[{i + 1}] {file}")

    while True:
        try:
            choice = input(f"\nEnter the number of the database you want to analyze (1-{len(db_files)}): ")
            index = int(choice)
            # Validating the 1-based index
            if 1 <= index <= len(db_files):
                return db_files[index - 1]
            else:
                print("Invalid choice. Please select a valid number from the list.")
        except ValueError:
            print("Please enter a valid integer.")


def debug_presenca_absoluta():
    path = select_database_file()
    if not path:
        return

    print(f"\nAnalyzing: {path}")
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # 1. Fetch Start Time from METADATA
    start_time_epoch = 0.0
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='METADATA'")
    if cursor.fetchone():
        try:
            df_meta = pd.read_sql_query("SELECT * FROM METADATA", conn)
            start_time_epoch = float(df_meta[df_meta['field'] == 'date_time']['value'].iloc[0])
        except Exception as e:
            print(f"Could not extract start time from METADATA: {e}")
    else:
        print("Warning: METADATA table not found. Defaulting to epoch 0.")

    # 2. Identify ROI tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ROI_%' AND name NOT LIKE '%MAP%'")
    tables = [t[0] for t in cursor.fetchall()]
    tables.sort(key=lambda x: int(''.join(filter(str.isdigit, x))) if any(char.isdigit() for char in x) else 0)

    # 3. Check for IMG_SNAPSHOTS (using COLLATE NOCASE to handle both lower and upper case)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name COLLATE NOCASE = 'img_snapshots'")
    snap_row = cursor.fetchone()
    has_snapshots = snap_row is not None
    snap_table_name = snap_row[0] if has_snapshots else None

    # Prepare Y-axis labels
    y_labels = tables.copy()
    if has_snapshots:
        y_labels.append("IMG_SNAPSHOTS")

    fig, ax = plt.subplots(figsize=(12, 8))

    # Convert threshold from minutes to milliseconds
    gap_threshold_ms = THRESHOLD_GAP_MINUTOS * 60 * 1000

    print("Analyzing gaps and snapshots...")

    # Draw ROI data
    for i, table in enumerate(tables):
        df = pd.read_sql_query(f"SELECT t FROM {table} ORDER BY t", conn)

        if df.empty:
            ax.text(0, i, f" {table} (EMPTY)", color='red', va='center', fontsize=9)
            continue

        # Convert relative 't' (ms) to absolute datetime using start_time_epoch
        df['datetime'] = pd.to_datetime(start_time_epoch + (df['t'] / 1000.0), unit='s')

        # Detect jumps (gaps) using the difference in milliseconds
        diffs = df['t'].diff()
        gap_indices = diffs[diffs > gap_threshold_ms].index.tolist()
        indices = [0] + gap_indices + [len(df)]

        # Draw the data segments
        for s, e in zip(indices[:-1], indices[1:]):
            segment_dt = df['datetime'].iloc[s:e]
            if not segment_dt.empty:
                ax.hlines(i, segment_dt.min(), segment_dt.max(), colors='blue', linewidth=5, alpha=0.7)

    # Draw snapshots, if they exist
    if has_snapshots:
        snapshot_idx = len(tables)  # Place on the row above the last ROI
        df_snap = pd.read_sql_query(f"SELECT t FROM {snap_table_name} ORDER BY t", conn)

        if not df_snap.empty:
            # Convert snapshot relative time to absolute time
            df_snap['datetime'] = pd.to_datetime(start_time_epoch + (df_snap['t'] / 1000.0), unit='s')

            # Use scatter plot with vertical markers for discrete events
            ax.scatter(df_snap['datetime'], [snapshot_idx] * len(df_snap),
                       color='green', marker='|', s=100, label='Snapshots', alpha=0.8)
        else:
            ax.text(0, snapshot_idx, " IMG_SNAPSHOTS (EMPTY)", color='red', va='center', fontsize=9)

    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Absolute Time")
    ax.set_title(
        f"Interruption and Snapshot Analysis - {os.path.basename(path)}\n(White spaces = Gaps > {THRESHOLD_GAP_MINUTOS} min)")

    # Format the x-axis to show absolute date and time (including seconds for better granularity)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    fig.autofmt_xdate()  # Automatically rotates dates so they don't overlap

    ax.grid(True, axis='x', linestyle='--', alpha=0.3)

    # Add legend if snapshots exist
    if has_snapshots:
        ax.legend(loc='upper right')

    plt.tight_layout()

    output_img = "debug_interrupcoes_absolutas.png"
    plt.savefig(output_img, dpi=200)
    plt.show()
    conn.close()
    print(f"Graph saved at: {os.path.abspath(output_img)}")


if __name__ == "__main__":
    debug_presenca_absoluta()