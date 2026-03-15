#!/bin/bash
#SBATCH --job-name=split_tasks
#SBATCH --output=logs/split_tasks_%j.out
#SBATCH --error=logs/split_tasks_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

# ===== Load Conda =====
source ~/.bashrc
conda activate multiarm
cd ~/decentralized-multiarm

# Run your script
python python tasks_split.py obstacle_v1