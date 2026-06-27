#!/bin/bash
#SBATCH --job-name=bitstar-expert
#SBATCH --partition=MGPU-TC2
#SBATCH --qos=q_m1x24
#SBATCH --output=logs/bitstar_%j.out
#SBATCH --error=logs/bitstar_%j.err
#SBATCH --ntasks=1
#SBATCH --nodelist=TC2N08
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=10
#SBATCH --time=24:00:00

# ===== Load Conda =====
source ~/.bashrc

# Activate conda environment
conda activate multiarm2

# Move to project directory
cd ~/decentralized-multiarm

# Run your scriptpython 
python omplExpertGenerator.py obstacle_v1 obstacle_v1_bitstar 10 --partition even
#python omplExpertGenerator.py base_test obstacle_v1_bitstar 4