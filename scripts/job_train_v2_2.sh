#!/bin/bash
#SBATCH --job-name=dma-train
#SBATCH --output=logs/train_v2_%j.out
#SBATCH --error=logs/train_v2_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

source ~/.bashrc

conda activate multiarm
cd ~/decentralized-multiarm

python main.py \
  --mode train \
  --name obstacle_v2 \
  --config configs/obstacle_v1.json \
  --tasks_path tasks/obstacle_v1_2 \
  --expert_waypoints experts/obstacle_v1_2 \
  --num_processes 10 \