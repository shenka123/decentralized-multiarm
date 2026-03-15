import json
import os
import sys
import shutil


def iter_json_files(root):
    with os.scandir(root) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                yield from iter_json_files(entry.path)
            elif entry.name.endswith('.json'):
                yield entry.path



# def copy_tasks(task_dir: Path, experts_dir: Path, field: str | None) -> None:
#     if not task_dir.is_dir():
#         raise SystemExit(f"Error: '{task_dir}' is not a directory.")

#     json_files = sorted(task_dir.glob("*.json"))
#     if not json_files:
#         raise SystemExit(f"No .json files found in '{task_dir}'.")

#     experts_present = experts_dir.is_dir()
#     if not experts_present:
#         print(f"Warning: experts directory '{experts_dir}' not found — skipping .npy copies.\n")

#     base_task    = str(task_dir).rstrip("/\\")
#     base_experts = str(experts_dir).rstrip("/\\")

#     task_copied, npy_copied, npy_missing = 0, 0, 0

#     for src_json in json_files:
#         with open(src_json) as f:
#             try:
#                 data = json.load(f)
#             except json.JSONDecodeError as e:
#                 print(f"  [skip] {src_json.name} — invalid JSON: {e}")
#                 continue

#         try:
#             k = find_arm_count(data, field)
#         except KeyError as e:
#             print(f"  [skip] {src_json.name} — {e}")
#             continue

#         stem = src_json.stem  # e.g. "12"

#         # --- copy JSON ---
#         dest_task_dir = Path(f"{base_task}_{k}")
#         dest_task_dir.mkdir(parents=True, exist_ok=True)
#         shutil.copy2(src_json, dest_task_dir / src_json.name)
#         print(f"  {src_json}  ->  {dest_task_dir / src_json.name}")
#         task_copied += 1

#         # --- copy .npy ---
#         if experts_present:
#             src_npy = experts_dir / f"{stem}.npy"
#             if src_npy.exists():
#                 dest_exp_dir = Path(f"{base_experts}_{k}")
#                 dest_exp_dir.mkdir(parents=True, exist_ok=True)
#                 shutil.copy2(src_npy, dest_exp_dir / src_npy.name)
#                 print(f"  {src_npy}  ->  {dest_exp_dir / src_npy.name}")
#                 npy_copied += 1
#             else:
#                 print(f"  [warn]  {src_npy} not found — skipped")
#                 npy_missing += 1

#     print(f"\nDone.")
#     print(f"  Tasks copied : {task_copied}/{len(json_files)}")
#     if experts_present:
#         print(f"  .npy copied  : {npy_copied}  |  missing: {npy_missing}")

# def get_arms(task):
#     with open(src_json) as f:
#         data = json.load(f)


if __name__ == "__main__":
    name=sys.argv[1]

    tasks_dir = f'tasks/{name}/'
    experts_dir = f'experts/{name}/'

    
    for d in [f'{dirs}/{name}_{i+1}/' for dirs in ['tasks', 'experts'] for i in range(4)]:
        os.makedirs(d, exist_ok=True)
        

    stats = {i+1:0 for i in range(4)}
    no_experts = []

    for task_file in iter_json_files(tasks_dir):
        filename = os.path.basename(task_file)
    
        with open(task_file) as f:
            task_data = json.load(f)
        
        num_arms = min(len(task_data['base_poses']),4)

        for a in range(num_arms):
            target_file = task_file.replace(f'/{filename}', f'_{a+1}/{filename}')
            shutil.copyfile(task_file, target_file)

        try:
            expert_filename = filename.replace(".json", ".npy")
            expert_file = experts_dir + expert_filename
            for a in range(num_arms):
                target_expert_file = expert_file.replace(f'/{expert_filename}', f'_{a+1}/{expert_filename}')
                shutil.copyfile(expert_file, target_expert_file)
        except:
            no_experts.append(filename)

        stats[num_arms] += 1

    print(f'Success: {sum(stats.values())}')
    for i in range(4):
        print(f'{i+1}: {stats[i+1]}')
    
    print(f'No experts: {len(no_experts)}')
    for t in no_experts:
        print(t)


