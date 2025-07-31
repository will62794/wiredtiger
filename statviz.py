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

    return timestamps, values

def plot_stat(timestamps, values, stat_path):
    plt.plot(timestamps, values)
    plt.title(stat_path)
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('stats.png')
    plt.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python plot_wt_stats.py <path_to_file> <stat.path.to.metric>")
        sys.exit(1)

    file_path = sys.argv[1]
    stat_path = sys.argv[2]
    ts_list = []
    vals_list = []
    for path in stat_path.split(','):
        ts, vals = load_stats(file_path, path.strip())
        ts_list.append(ts)
        vals_list.append(vals)
        
    plt.figure()
    for i, (ts, vals, path) in enumerate(zip(ts_list, vals_list, stat_path.split(','))):
        plt.plot(ts, vals, label=path.strip())
    plt.title("Multiple Stats")
    plt.xlabel("Time") 
    plt.ylabel("Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig('stats.png')
    plt.close()