#!/bin/bash
#SBATCH --job-name=split_tasks
#SBATCH --output=logs/split_tasks_%j.out
#SBATCH --error=logs/split_tasks_%j.err
#SBATCH --ntasks=1
#SBATCH --time=06:00:00

# ===== Load Conda =====
source ~/.bashrc
conda activate multiarm
cd ~/decentralized-multiarm

rm -rf tasks/obstacle_v1_1/ tasks/obstacle_v1_2/ tasks/obstacle_v1_3/ tasks/obstacle_v1_4/ experts/obstacle_v1_1/ experts/obstacle_v1_2/ experts/obstacle_v1_3/ experts/obstacle_v1_4/


# Run your script
python tasks_split.py obstacle_v1