#!/bin/bash
#SBATCH --job-name=obs-gen
#SBATCH --output=logs/obstacle_%j.out
#SBATCH --error=logs/obstacle_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00


# ===== Load Conda =====
source ~/.bashrc

# Activate conda environment
conda activate multiarm

# Move to project directory
cd ~/decentralized-multiarm

# Run your script
python obstacleGenerator.py base obstacle_v1 10