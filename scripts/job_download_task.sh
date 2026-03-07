#!/bin/bash
#SBATCH --job-name=task_dl
#SBATCH --output=logs/task_dl_%j.out
#SBATCH --error=logs/task_dl_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00


# ===== Load Conda =====
source ~/.bashrc

# Activate conda environment
conda activate multiarm

# Move to project directory
cd ~/decentralized-multiarm
mkdir -p tasks/base && wget -qO- https://multiarm.cs.columbia.edu/downloads/data/tasks.tar.xz | tar xfJ - -C tasks/base/ --strip-components=1

# Run your script
python obstacleGenerator.py base obstacle_v1 10