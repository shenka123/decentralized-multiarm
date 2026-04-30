#!/bin/bash
#SBATCH --job-name=dma-train
#SBATCH --partition=MGPU-TC2
#SBATCH --qos=q_m1x24
#SBATCH --output=logs/train_v2_%j.out
#SBATCH --error=logs/train_v2_%j.err
#SBATCH --ntasks=1
#SBATCH --nodelist=TC2N08
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=10
#SBATCH --time=24:00:00

source ~/.bashrc

conda activate multiarm
cd ~/decentralized-multiarm


python main.py \
  --mode train \
  --name obstacle_v3 \
  --config configs/obstacle_v1.json \
  --tasks_path tasks/obstacle_v1 \
  --expert_waypoints experts/obstacle_v1/ \
  --max_time 24 \
  --num_processes 10 