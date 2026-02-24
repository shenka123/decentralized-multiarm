#!/bin/bash
#SBATCH --job-name=decentralized_multiarm_train
#SBATCH --output=logs/train_%j.out
#SBATCH --error=logs/train_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00

source ~/.bashrc

conda activate multiarm
cd ~/decentralized-multiarm

python main.py \
  --mode train \
  --name obstacle_v1 \
  --config configs/obstacle_v1.json \
  --tasks_path tasks/obstacle_v1 \
  --expert_waypoints experts/obstacle_v1 \
  --num_processes 8