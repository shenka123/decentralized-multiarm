#!/bin/bash
#SBATCH --job-name=dma-evaluate
#SBATCH --output=logs/evaluate_%j.out
#SBATCH --error=logs/evaluate_%j.err
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --nodelist=TC2N07
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

source ~/.bashrc

conda activate multiarm
cd ~/decentralized-multiarm


python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"

module load cuda/12.8.0 
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"

python main.py \
  --mode benchmark \
  --name benchmark_multiarm \
  --config configs/obstacle_v1_short.json \
  --load runs/obstacle_v3/ckpt_multiarm_motion_planner_01175 \
  --max_time 3 \
  --num_processes 10 \
  --tasks_path tasks/obstacle_evaluate \
  --gui

  
python main.py \
  --mode benchmark \
  --name benchmark_multiarm_dense \
  --config configs/obstacle_v1_short.json \
  --load runs/obstacle_v3/ckpt_multiarm_motion_planner_01725 \
  --max_time 3 \
  --num_processes 10 \
  --tasks_path tasks/obstacle evaluate \
  --gui