#!/bin/bash
#SBATCH --job-name=dma-train
#SBATCH --partition=MGPU-TC2
#SBATCH --qos=q_m1x24
#SBATCH --output=logs/train_v7_%j.out
#SBATCH --error=logs/train_v7_%j.err
#SBATCH --ntasks=1
#SBATCH --nodelist=TC2N08
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

source ~/.bashrc

conda activate multiarm
cd ~/decentralized-multiarm


python main.py \
  --mode train \
  --name obstacle_v7 \
  --config configs/obstacle_v7.json \
  --tasks_path tasks/obstacle_v1 \
  --expert_waypoints experts/obstacle_v1_bitstar/ \
  --max_time 6 \
  --num_processes 10
