#!/bin/bash
#SBATCH --job-name=hw-info
#SBATCH --partition=MGPU-TC2
#SBATCH --output=logs/hw_info_%j.out
#SBATCH --error=logs/hw_info_%j.err
#SBATCH --ntasks=1
#SBATCH --nodelist=TC2N08
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=10
#SBATCH --time=00:10:00

# Prints the hardware and software versions of the compute node for the
# Experimental Setup section of the report.

source ~/.bashrc

echo "== Node =="
hostname
cat /etc/os-release | grep PRETTY_NAME
uname -r

echo "== CPU =="
lscpu | grep -E "Model name|^CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)"
echo "CPUs allocated to job: $SLURM_CPUS_PER_TASK"

echo "== RAM =="
free -h | grep Mem

echo "== GPU =="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
nvidia-smi | grep "CUDA Version"

cd ~/decentralized-multiarm
for env in multiarm multiarm2; do
    echo "== Software ($env) =="
    conda activate $env
    python --version
    python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)"
    python -c "import pybullet; print('pybullet API', pybullet.getAPIVersion())"
    python -c "import ray; print('ray', ray.__version__)"
    python -c "import numpy; print('numpy', numpy.__version__)"
    python -c "import ompl; print('ompl', getattr(ompl, '__version__', 'see conda list'))" 2>&1
    conda list | grep -iE "^(ompl|pybullet|pytorch|torch) "
    conda deactivate
done
