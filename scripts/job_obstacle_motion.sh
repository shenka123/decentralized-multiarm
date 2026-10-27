#!/bin/bash
#SBATCH --job-name=obs-motion-gen
#SBATCH --output=logs/obstacle_motion_%j.out
#SBATCH --error=logs/obstacle_motion_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=02:00:00


# ===== Load Conda =====
source ~/.bashrc

# Activate conda environment
conda activate multiarm

# Move to project directory
cd ~/decentralized-multiarm

# Add movement seeds to the evaluation tasks (static tasks are left untouched).
# "reset" reprocesses every task and overwrites same-name files in
# tasks/obstacle_evaluate_moving/
python obstacleMotionGenerator.py obstacle_evaluate obstacle_evaluate_moving 10 reset
