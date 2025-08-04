#!/usr/bin/env python3
"""
Python equivalent of runperf.sh - WiredTiger performance testing script
"""

import subprocess
import os
import glob
import shutil
import sys
import argparse

import json
import matplotlib.pyplot as plt
from datetime import datetime


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
                values.append((stat_path,val))
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

def plot_stats(file_path, stat_path, png_output_path):
    ts_list = []
    vals_list = []
    for path in stat_path.split(','):
        ts, vals = load_stats(file_path, path.strip())
        ts_list.append(ts)
        vals_list.append(vals)
        
    plt.figure()
    for i, (ts, vals, path) in enumerate(zip(ts_list, vals_list, stat_path.split(','))):
        plt.plot(ts, [v[1] for v in vals], label=path.strip())

    # Goodput from wiredTiger.transaction.transactions committed final stat number.
    ts, vals = load_stats(file_path, "wiredTiger.transaction.update conflicts")
    update_conflicts = vals[-1][1]

    ts, vals = load_stats(file_path, "wiredTiger.transaction.transactions rolled back")
    txns_rolled_back = vals[-1][1]


    ts, vals = load_stats(file_path, "wiredTiger.transaction.transactions committed")
    txns_committed = vals[-1][1]
    goodput = vals[-1][1] / ts[-1]
    # print(vals)
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

    # print(f"")
    print(f"Goodput: {goodput:,.2f} txns/sec")
    print(f"Update conflicts: {update_conflicts:.2f}")
    print(f"Transactions committed: {txns_committed:.2f}")
    print(f"Transactions rolled back: {txns_rolled_back:.2f}")
    print(f"Conflict rate: {100 * update_conflicts/(txns_committed+txns_rolled_back):.2f}%")    

def run_test(read_stable, num_threads, viz_only=False):
    """
    Python equivalent of the run_test bash function.
    
    Args:
        read_stable (bool): Whether to use read_stable mode
        num_threads (int): Number of threads to use
        viz_only (bool): If True, skip running tests and only generate visualizations
    
    Returns:
        dict: Statistics results if successful, None otherwise
    """
    # Store original directory
    original_dir = os.getcwd()
    
    try:
        # Change to wtperf directory
        wtperf_dir = "build/bench/wtperf"
        os.chdir(wtperf_dir)
        
        # Create home directory name
        homedir = f"wt_home_read_stable_{read_stable}_{num_threads}threads"
        
        if not viz_only:
            print(f"--- Running test with read_stable={read_stable} and {num_threads} threads")
            
            # Remove existing home directory if it exists
            if os.path.exists(homedir):
                shutil.rmtree(homedir)
            
            # Create home directory
            os.makedirs(homedir)
            
            # Run populate
            print("Running populate")
            subprocess.run([
                "./wtperf", "-h", homedir, 
                "-O", "../../../bench/wtperf/runners/500m-btree-populate.wtperf"
            ], check=True)
            
            # Run workload
            print("Running workload")
            runtime_secs = 10
            threads = f"((count={num_threads},reads=1,inserts=9,ops_per_txn=10))"
            config = f"read_stable={read_stable},threads={threads},pareto=50,run_time={runtime_secs}"
            
            subprocess.run([
                "./wtperf", "-h", homedir,
                "-O", "../../../bench/wtperf/runners/500m-btree-80r20u.wtperf",
                "-o", config
            ], check=True)
            
            # Display test statistics (filtered)
            test_stat_file = os.path.join(homedir, "test.stat")
            if os.path.exists(test_stat_file):
                with open(test_stat_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not any(skip in line for skip in [
                            "checkpoint operations", "backup operations", 
                            "flush_tier operations", "truncate operations", "scan operations"
                        ]):
                            print(line)
        
        # Find stat file
        stat_files = glob.glob(os.path.join(homedir, "WiredTigerStat.*"))
        if not stat_files:
            print(f"Warning: No WiredTigerStat files found in {homedir}")
            return None
        
        statfile = stat_files[0]
        print(statfile)
        
        # Generate visualization using statviz.py
        stats = "wiredTiger.transaction.update conflicts,wiredTiger.transaction.transactions rolled back"
        output_file = f"stats_read_stable_{read_stable}.png"
        
        # # Call statviz.py to generate the visualization
        # subprocess.run([
        #     sys.executable, "statviz.py", statfile, stats, output_file
        # ], check=True)

        ts, vals = load_stats(statfile, "wiredTiger.transaction.transactions committed")
        txns_committed = vals[-1][1]
        print(txns_committed)

        # ts, txns_rolled_back = load_stats(statfile, "wiredTiger.transaction.transactions rolled back")[-1][1]
        # update_conflicts = load_stats(statfile, "wiredTiger.transaction.update conflicts")[-1][1]
        goodput = txns_committed / ts[-1]
        print(f"Goodput: {goodput:,.2f} txns/sec")
        
        return {
            'statfile': statfile,
            'goodput': goodput,
            'output_file': output_file,
            'homedir': homedir
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Error running wtperf command: {e}")
        return None
    except Exception as e:
        print(f"Error in run_test: {e}")
        return None
    finally:
        # Return to original directory
        os.chdir(original_dir)

def main():
    """Main function to handle command-line arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run WiredTiger performance tests')
    parser.add_argument('--viz-only', action='store_true', 
                      help='Skip running tests and only generate visualizations')
    parser.add_argument('--threads', type=str, default='2,4,6,8,10,12,14',
                      help='Comma-separated list of thread counts to test')
    parser.add_argument('--read-stable', action='store_true',
                      help='Enable read_stable mode (default: False)')
    
    args = parser.parse_args()
    
    thread_counts = [int(t.strip()) for t in args.threads.split(',')]
    
    print(f"Running tests with thread counts: {thread_counts}")
    print(f"Read stable: {args.read_stable}")
    print(f"Viz only: {args.viz_only}")
    
    results = []
    read_stable_str = "true" if args.read_stable else "false"
    for nthreads in thread_counts:
        print(f"\n{'='*50}")
        result = run_test(read_stable_str, nthreads, args.viz_only)
        if result:
            results.append((nthreads, result))
            print(f"Test completed successfully for {nthreads} threads")
        else:
            print(f"Test failed for {nthreads} threads")

    # Generate throughput vs threads plot
    if results:
        plt.figure()
        thread_counts = []
        throughputs = []
        
        for nthreads, result in results:
            # Load the final throughput value for each thread count
            # ts, vals = load_stats(result['statfile'], "wiredTiger.transaction.transactions committed")
            # throughput = vals[-1][1] / ts[-1]  # transactions / total time
            goodput = result['goodput']
            thread_counts.append(nthreads)
            throughputs.append(goodput)

        plt.plot(thread_counts, throughputs, marker='o')
        plt.title("Throughput vs Number of Threads")
        plt.xlabel("Number of Threads")
        plt.ylabel("Throughput (txns/sec)")
        plt.grid(True)
        plt.tight_layout()
        
        # Save with a descriptive name including read_stable setting
        read_stable_str = "read_stable" if args.read_stable else "no_read_stable"
        plt.savefig(f'throughput_vs_threads_{read_stable_str}.png')
        plt.close()
    
    # Print summary
    if results:
        print(f"\n{'='*50}")
        print("SUMMARY:")
        print(f"{'Threads':<8} {'Status':<15} {'Output File':<30}")
        print("-" * 50)
        for nthreads, result in results:
            print(f"{nthreads:<8} {'Success':<15} {result['output_file']:<30}")
    else:
        print("No tests completed successfully.")

if __name__ == "__main__":
    main() 