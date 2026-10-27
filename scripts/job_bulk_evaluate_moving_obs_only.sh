#!/bin/bash
#SBATCH --job-name=dma-bulk-evaluate-moving-obs
#SBATCH --output=logs/bulk_evaluate_moving_obs_%j.out
#SBATCH --error=logs/bulk_evaluate_moving_obs_%j.err
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
TASKS_DIR=tasks/obstacle_evaluate_moving

if [ ! -d "$TASKS_DIR" ]; then
    echo "[RemoveNoObstacle] $TASKS_DIR does not exist"
    exit 1
fi

# Delete tasks without obstacles ("obstacles" missing, null or empty).
# Files with "config" in their path are skipped, matching TaskLoader.
python - "$TASKS_DIR" <<'EOF' || exit 1
import json
import sys
from pathlib import Path

tasks_dir = Path(sys.argv[1])
files = [f for f in tasks_dir.rglob('*.json') if 'config' not in str(f)]
removed = 0
for f in files:
    try:
        obstacles = json.load(open(f)).get('obstacles')
    except (json.JSONDecodeError, OSError) as e:
        print('[RemoveNoObstacle] Skipping unreadable', f, '-', e)
        continue
    if not obstacles:
        f.unlink()
        removed += 1
print('[RemoveNoObstacle] Removed {} of {} tasks in {}, {} left'.format(
    removed, len(files), tasks_dir, len(files) - removed))
EOF

# Edit configs/bulk_evaluate_moving.json to change the checkpoints; outputs go to
# benchmark/bulk/<run timestamp>/
python bulk_evaluate.py configs/bulk_evaluate_moving.json
