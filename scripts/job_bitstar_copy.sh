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
conda activate multiarm2

# Move to project directory
cd ~/decentralized-multiarm

# Run your scriptpython 
for f in experts/obstacle_v1_bitstar/*; do
    base="${f##*/}"
    base="${base%.*}"
    for src in experts/obstacle_v1/"$base".*; do
        [ -e "$src" ] || continue
        dest="experts/obstacle_v1_bitstar/${src##*/}"
        if [ ! -e "$dest" ]; then
            echo "Copying: ${src##*/}"
            cp "$src" "$dest"
        fi
    done
done