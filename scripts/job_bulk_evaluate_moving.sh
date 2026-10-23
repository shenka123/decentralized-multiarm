#!/bin/bash
#SBATCH --job-name=dma-bulk-evaluate-moving
#SBATCH --output=logs/bulk_evaluate_moving_%j.out
#SBATCH --error=logs/bulk_evaluate_moving_%j.err
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

source ~/.bashrc

conda activate multiarm2
cd ~/decentralized-multiarm

module load cuda/12.8.0
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"

# Run scripts/job_obstacle_motion.sh first to create tasks/obstacle_evaluate_moving.
# Edit configs/bulk_evaluate_moving.json to change the checkpoints; outputs go to
# benchmark/bulk/<run timestamp>/
python bulk_evaluate.py configs/bulk_evaluate_moving.json
