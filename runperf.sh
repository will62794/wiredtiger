
#!/bin/bash

run_test() {
    cd build/bench/wtperf
    read_stable=$1
    homedir=wt_home_read_stable_${read_stable}
    rm -rf $homedir
    mkdir $homedir
    echo "Running populate"
    ./wtperf -h $homedir -O ../../../bench/wtperf/runners/500m-btree-populate.wtperf
    echo "Running workload"
    ./wtperf -h $homedir -O ../../../bench/wtperf/runners/500m-btree-80r20u.wtperf -o read_stable=$read_stable
    cat $homedir/test.stat | grep -v "checkpoint operations" \
        | grep -v "backup operations" | grep -v "flush tier operations" | grep -v "truncate operations"
    cd -

    statfile=$(ls build/bench/wtperf/$homedir/WiredTigerStat.* | head -n 1)
    echo $statfile
    stats="wiredTiger.transaction.update conflicts,wiredTiger.transaction.transactions rolled back,wiredTiger.transaction.transactions committed"
    python3 statviz.py $statfile "$stats" stats_read_stable_${read_stable}.png
}

echo "--- Running test with read_stable=false" 
run_test false

echo "--- Running test with read_stable=true"
run_test true



