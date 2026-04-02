#!/bin/bash
#SBATCH --job-name=dma-train
#SBATCH --output=logs/train_v2_%j.out
#SBATCH --error=logs/train_v2_%j.err
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --nodelist=TC2N08
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

source ~/.bashrc

conda activate multiarm
cd ~/decentralized-multiarm


python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"

module load cuda/12.8.0 
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"


python main.py \
  --mode train \
  --name obstacle_v3 \
  --config configs/obstacle_v1.json \
  --tasks_path tasks/obstacle_v1 \
  --expert_waypoints experts/obstacle_v1/ \
  --num_processes 10 