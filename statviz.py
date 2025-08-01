import json
import matplotlib.pyplot as plt
from datetime import datetime
import sys

def load_stats(file_path, stat_path):
    timestamps = []
    values = []

    with open(file_path) as f:
        for line in f:
            try:
                data = json.loads(line)
                ts = datetime.fromisoformat(data["localTime"].replace("Z", "+00:00"))
                val = data
                for part in stat_path.split('.'):
                    val = val[part]
                timestamps.append(ts)
                values.append(val)
            except Exception as e:
                print(f"Skipping line due to error: {e}")
                continue

    # Convert timestamps to seconds from start
    start_time = timestamps[0]
    timestamps = [(ts - start_time).total_seconds() for ts in timestamps]
    return timestamps, values

def plot_stat(timestamps, values, stat_path):
    plt.plot(timestamps, values)
    plt.title(stat_path)
    plt.xlabel("Time (seconds)")
    plt.ylabel("Value")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('stats.png')
    plt.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python plot_wt_stats.py <path_to_file> <stat.path.to.metric> <png_output_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    stat_path = sys.argv[2]
    png_output_path = sys.argv[3]
    ts_list = []
    vals_list = []
    for path in stat_path.split(','):
        ts, vals = load_stats(file_path, path.strip())
        ts_list.append(ts)
        vals_list.append(vals)
        
    plt.figure()
    for i, (ts, vals, path) in enumerate(zip(ts_list, vals_list, stat_path.split(','))):
        plt.plot(ts, vals, label=path.strip())

    # Goodput from wiredTiger.transaction.transactions committed final stat number.
    goodput = vals_list[-1][-1] / ts_list[-1][-1]
    plt.annotate(f'Goodput: {goodput:.2f} txns/sec', 
                xy=(0.02, 0.68), 
                xycoords='axes fraction',
                bbox=dict(facecolor='white', alpha=0.8))

    plt.title("Multiple Stats")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(png_output_path)
    plt.close()