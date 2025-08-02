
#!/bin/bash
VIZONLY=false
run_test() {
    cd build/bench/wtperf
    read_stable=$1
    num_threads=$2
    homedir=wt_home_read_stable_${read_stable}_${num_threads}threads
    
    if [ "$VIZONLY" = false ]; then
        echo "--- Running test with read_stable=$read_stable and $num_threads threads" 
        rm -rf $homedir
        mkdir $homedir
        echo "Running populate"
        ./wtperf -h $homedir -O ../../../bench/wtperf/runners/500m-btree-populate.wtperf
        echo "Running workload"
        threads="((count=$num_threads,reads=2,updates=8,ops_per_txn=10))"
        config="read_stable=$read_stable,threads=$threads,pareto=80"
        ./wtperf -h $homedir -O ../../../bench/wtperf/runners/500m-btree-80r20u.wtperf -o $config
        cat $homedir/test.stat | grep -v "checkpoint operations" \
            | grep -v "backup operations" | grep -v "flush_tier operations" | grep -v "truncate operations" \
            | grep -v "scan operations"
    fi
    cd -

    statfile=$(ls build/bench/wtperf/$homedir/WiredTigerStat.* | head -n 1)
    echo $statfile
    # stats="wiredTiger.transaction.update conflicts,wiredTiger.transaction.transactions rolled back,wiredTiger.transaction.transactions committed"
    stats="wiredTiger.transaction.update conflicts,wiredTiger.transaction.transactions rolled back"
    python3 statviz.py $statfile "$stats" stats_read_stable_${read_stable}.png
}

if [ "$1" = "vizonly" ]; then
    VIZONLY=true
fi
    
# Run tests.
for nthreads in 10; do
    run_test false $nthreads
    run_test true $nthreads
done
