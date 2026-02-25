#!/bin/bash
#SBATCH --job-name=birrt_recount
#SBATCH --output=logs/birrt_recount_%j.out
#SBATCH --error=logs/birrt_recount_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

# ===== Load Conda =====
source ~/.bashrc
conda activate multiarm
cd ~/decentralized-multiarm

# Run your script
python obstacleGeneratorLogs.py obstacle_v1