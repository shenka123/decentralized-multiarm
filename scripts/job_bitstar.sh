#!/bin/bash
#SBATCH --job-name=bitstar-expert
#SBATCH --output=logs/bitstar_%j.out
#SBATCH --error=logs/bitstar_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00


# ===== Load Conda =====
source ~/.bashrc

# Activate conda environment
conda activate multiarm

# Move to project directory
cd ~/decentralized-multiarm

# Run your scriptpython 
python omplExpertGenerator.py obstacle_v1 obstacle_v1_bitstar 10s