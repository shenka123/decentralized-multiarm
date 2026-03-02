#!/bin/bash
#SBATCH --job-name=dma-train
#SBATCH --output=logs/train_v1_%j.out
#SBATCH --error=logs/train_v1_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
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
  --num_processes 10 \
  --load runs/obstacle_v1/ckpt_multiarm_motion_planner_00090