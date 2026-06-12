#!/bin/bash
#SBATCH --job-name=ompl-benchmark
#SBATCH --output=logs/ompl_benchmark_%j.out
#SBATCH --error=logs/ompl_benchmark_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

source ~/.bashrc
conda activate multiarm2
cd ~/decentralized-multiarm

mkdir -p benchmark logs

TASKS=tasks/obstacle_evaluate
CONFIG=configs/evaluate.json
TIMEOUT=30
STAMP=$(date +%Y%m%d_%H%M%S)

for PLANNER in RRTConnect RRT BITstar PRM LBKPIECE; do
    echo "========================================"
    echo "Running planner: $PLANNER"
    echo "========================================"
    python benchmark.py \
        --config $CONFIG  \
        --tasks_path $TASKS \
        --planner $PLANNER \
        --timeout $TIMEOUT \
        --name ${STAMP}_${PLANNER}
done

echo "All planners done. Summarizing results..."

for PLANNER in RRTConnect RRT BITstar PRM LBKPIECE; do
    PKL="benchmark/${STAMP}_${PLANNER}_score.pkl"
    if [ -f "$PKL" ]; then
        echo ""
        echo "=== $PLANNER ==="
        python summary.py "$PKL"
    else
        echo "No output found for $PLANNER at $PKL"
    fi
done