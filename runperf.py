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
import colorsys


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

def run_test(read_stable, num_threads, viz_only=False, rw_ratio=0.5, runtime_secs=20, pareto=10):
    """
    Python equivalent of the run_test bash function.
    
    Args:
        read_stable (bool): Whether to use read_stable mode
        num_threads (int): Number of threads to use
        viz_only (bool): If True, skip running tests and only generate visualizations
        rw_ratio (float): Ratio of reads to total operations
        runtime_secs (int): Runtime in seconds for each test
        pareto (int): Pareto parameter for key distribution
    
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
        homedir_root = "wtperf_data"
        homedir = f"{homedir_root}/wt_home_read_stable_{read_stable}_{num_threads}threads_rw{rw_ratio}"
        
        if not viz_only:
            print(f"--- Running test with read_stable={read_stable}, {num_threads} threads, rw_ratio={rw_ratio}")
            
            # Remove existing home directory if it exists
            if os.path.exists(homedir_root):
                shutil.rmtree(homedir_root)
                # shutil.rmtree(homedir)
            
            # Create home directory
            os.makedirs(homedir_root)
            os.makedirs(homedir)
            
            # Run populate
            print("Running populate")
            subprocess.run([
                "./wtperf", "-h", homedir, 
                "-O", "../../../bench/wtperf/runners/500m-btree-populate.wtperf"
            ], check=True)
            
            # Run workload
            print("Running workload")

            # Some config parameters.
            ops_per_txn = 40
            warmup_secs = 90
            threads_config = f"((count={num_threads},reads={int(rw_ratio*ops_per_txn)},updates={int((1-rw_ratio)*ops_per_txn)},ops_per_txn={ops_per_txn}))"
            
            config_str = f"read_stable={read_stable},threads={threads_config},pareto={pareto},warmup={warmup_secs},run_time={runtime_secs}"
            
            subprocess.run([
                "./wtperf", "-h", homedir,
                "-O", "../../../bench/wtperf/runners/500m-btree-80r20u.wtperf",
                "-o", config_str
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
        output_file = f"stats_read_stable_{read_stable}_rw{rw_ratio}.png"
        
        ts, vals = load_stats(statfile, "wiredTiger.transaction.transactions committed")
        txns_committed = vals[-1][1]
        print(txns_committed)


        # transaction begins
        ts, vals = load_stats(statfile, "wiredTiger.transaction.transaction begins")
        # print(ts)
        # print(vals)
        txns_begins = vals[-1][1]

        ts, vals = load_stats(statfile, "wiredTiger.transaction.transactions rolled back")
        txns_rolled_back = vals[-1][1]

        print("txns_begins: ", txns_begins)
        print("txns_committed: {:,}".format(txns_committed))
        print("txns_aborted: {:,}".format(txns_rolled_back))

        goodput = txns_committed / ts[-1]
        print(f"Goodput: {goodput:,.2f} txns/sec")

        
        # print("Transactions rolled back: ", txns_rolled_back)
        abort_rate = 100 * txns_rolled_back/(txns_committed+txns_rolled_back)
        print("Abort rate: {:.2f}%".format(100 * txns_rolled_back/(txns_committed+txns_rolled_back)))
        
        return {
            'statfile': statfile,
            'goodput': goodput,
            'output_file': output_file,
            'homedir': homedir,
            'rw_ratio': rw_ratio,
            'abort_rate': abort_rate
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

def plot_all_results(all_results):
    plt.figure(figsize=(10, 6))
        
    # Define colors for different rw_ratios
    rw_ratio_colors = {
        0.5: '#1f77b4',  # blue
        0.8: '#2ca02c',  # green 
        0.2: '#ff7f0e',  # orange
        0.9: '#d62728',  # red
        0.1: '#9467bd',  # purple
    }
    
    linestyles = ['-', '--']  # Different line styles for read_stable
    markers = ['o', 's', '^', 'D', 'v', '<', '>']  # Different marker styles
    
    for i, ((read_stable, rw_ratio, pareto), results) in enumerate(all_results.items()):
        thread_counts = []
        throughputs = []
        abort_rates = []
        
        for nthreads, result in results:
            goodput = result['goodput']
            abort_rate = result['abort_rate']
            thread_counts.append(nthreads)
            throughputs.append(goodput)
            abort_rates.append(abort_rate)

        # Use a different color for each line from the default color cycle
        linestyle = linestyles[0] if read_stable == 'true' else linestyles[1]

        label = f"read_stable={read_stable}, rw_ratio={rw_ratio}, pareto={pareto}"
        line = plt.plot(thread_counts, throughputs,
                linestyle=linestyle, 
                marker=markers[i % len(markers)],
                markersize=8,
                label=label)
        
        # Add abort rate annotations next to each point
        for x, y, ar in zip(thread_counts, throughputs, abort_rates):
            plt.annotate(f'{ar:.1f}%', 
                        (x, y),
                        xytext=(-4, 10),
                        textcoords='offset points',
                        fontsize=8)
                        # bbox=dict(facecolor='white', edgecolor='none', alpha=1))

    plt.title("Throughput vs Number of Threads")
    plt.xlabel("Number of Threads")
    plt.ylabel("Throughput (txns/sec)")
    plt.grid(True)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    plt.savefig('txn_scalability_comparison.png', bbox_inches='tight')
    plt.close()

def main():
    """Main function to handle command-line arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run WiredTiger performance tests')
    parser.add_argument('--viz-only', action='store_true', 
                      help='Skip running tests and only generate visualizations')
    parser.add_argument('--threads', type=str, default='2,4,6,8,10,12,14',
                      help='Comma-separated list of thread counts to test')
    parser.add_argument('--read-stable', type=str, default='true,false',
                      help='Comma-separated list of read_stable values to test')
    parser.add_argument('--rw-ratio', type=str, default='0.5',
                      help='Comma-separated list of read/write ratios to test')
    parser.add_argument('--runtime_secs', type=int, default=20,
                      help='Runtime in seconds for each test')
    parser.add_argument('--pareto', type=str, default='10',
                      help='Comma-separated list of pareto parameters for key distribution')
    
    args = parser.parse_args()
    
    thread_counts = [int(t.strip()) for t in args.threads.split(',')]
    read_stable_values = [rs.strip().lower() for rs in args.read_stable.split(',')]
    rw_ratios = [float(r.strip()) for r in args.rw_ratio.split(',')]
    pareto_values = [int(p.strip()) for p in args.pareto.split(',')]
    
    print(f"Running tests with thread counts: {thread_counts}")
    print(f"Read stable values: {read_stable_values}")
    print(f"R/W ratios: {rw_ratios}")
    print(f"Runtime: {args.runtime_secs} seconds")
    print(f"Pareto values: {pareto_values}")
    print(f"Viz only: {args.viz_only}")
    
    all_results = {}
    for read_stable in read_stable_values:
        for rw_ratio in rw_ratios:
            for pareto in pareto_values:
                key = (read_stable, rw_ratio, pareto)
                results = []
                for nthreads in thread_counts:
                    print(f"\n{'='*50}")
                    result = run_test(read_stable, nthreads, args.viz_only, rw_ratio, args.runtime_secs, pareto)
                    if result:
                        results.append((nthreads, result))
                        print(f"Test completed successfully for {nthreads} threads with read_stable={read_stable}, rw_ratio={rw_ratio}, pareto={pareto}")
                    else:
                        print(f"Test failed for {nthreads} threads with read_stable={read_stable}, rw_ratio={rw_ratio}, pareto={pareto}")
                all_results[key] = results
                sys.stdout.flush()

                # Re-plot results (throughput vs threads plot with all configurations).
                plot_all_results(all_results)

    # Print summary
    if all_results:
        print(f"\n{'='*50}")
        print("SUMMARY:")
        print(f"{'Read Stable':<12} {'R/W Ratio':<10} {'Pareto':<8} {'Threads':<8} {'Status':<15} {'Output File':<30}")
        print("-" * 83)
        for (read_stable, rw_ratio, pareto), results in all_results.items():
            for nthreads, result in results:
                print(f"{read_stable:<12} {rw_ratio:<10.2f} {pareto:<8} {nthreads:<8} {'Success':<15} {result['output_file']:<30}")
    else:
        print("No tests completed successfully.")

if __name__ == "__main__":
    main() 