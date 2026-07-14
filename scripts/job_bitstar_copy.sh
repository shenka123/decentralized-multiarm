#!/bin/bash
#SBATCH --job-name=bitstar-expert
#SBATCH --output=logs/bitstar_%j.out
#SBATCH --error=logs/bitstar_%j.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --time=06:00:00


# ===== Load Conda =====
source ~/.bashrc

# Activate conda environment
conda activate multiarm2

# Move to project directory
cd ~/decentralized-multiarm


# ---- EDIT THESE PATHS ----
DIR_A="/experts/obstacle_v1/"
DIR_B="experts/obstacle_v1_bitstar/"
# ---------------------------

echo "Job started on $(hostname) at $(date)"
echo "Source (A): $DIR_A"
echo "Destination (B): $DIR_B"

if [ ! -d "$DIR_A" ]; then
    echo "ERROR: Source folder $DIR_A does not exist."
    exit 1
fi

if [ ! -d "$DIR_B" ]; then
    echo "Destination folder $DIR_B does not exist, creating it."
    mkdir -p "$DIR_B"
fi

# --ignore-existing: skip any file that already exists in B (by name),
#                     regardless of whether its content differs from A's version.
# -a                : archive mode, preserves permissions/timestamps, recurses into subdirs.
# -i                : itemized changes, one line per file, needed to build the summary below.
# --dry-run         : REMOVE this once you've verified the output below looks correct.

RSYNC_LOG=$(mktemp)

rsync -ai --ignore-existing --dry-run "$DIR_A"/ "$DIR_B"/ | tee "$RSYNC_LOG"

# Count results.
# Itemized lines for a copied regular file look like: ">f+++++++++ filename"
COPIED=$(grep -c '^>f' "$RSYNC_LOG")
TOTAL_A=$(find "$DIR_A" -type f | wc -l)
SKIPPED=$((TOTAL_A - COPIED))

echo "----"
echo "SUMMARY"
echo "  Files in A total : $TOTAL_A"
echo "  Copied to B      : $COPIED"
echo "  Skipped (already in B): $SKIPPED"
echo "----"
echo "Above is a DRY RUN. No files were copied yet."
echo "Remove --dry-run from the rsync command in this script to actually perform the copy."

rm -f "$RSYNC_LOG"

echo "Job finished at $(date)"
