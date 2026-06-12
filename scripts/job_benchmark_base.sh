#!/bin/bash
#SBATCH --job-name=ompl-benchmark
#SBATCH --output=logs/ompl_benchmark_%j.out
#SBATCH --error=logs/ompl_benchmark_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=00:10:00

source ~/.bashrc
conda activate multiarm2
cd ~/decentralized-multiarm

mkdir -p benchmark logs

TASKS=tasks/obstacle_evaluate
CONFIG=configs/evaluate.json
TIMEOUT=30
STAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================"
echo "Running RL Multiarm (base)"
echo "========================================"
python main.py \
  --mode benchmark \
  --name ${STAMP}_benchmark_multiarm_base \
  --config $CONFIG \
  --load runs/obstacle_v4/ckpt_multiarm_motion_planner_00000 \
  --max_time 0.2 \
  --num_processes 10 \
  --tasks_path $TASKS 
