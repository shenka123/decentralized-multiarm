#!/bin/bash
#SBATCH --job-name=check_gpu
#SBATCH --output=logs/check_gpu_%j.out
#SBATCH --error=logs/check_gpu_%j.err
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00

source ~/.bashrc

conda activate multiarm
cd ~/decentralized-multiarm

python test.py