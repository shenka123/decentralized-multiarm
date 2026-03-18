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

        for a in range(num_arms, 4):
            target_file = task_file.replace(f'/{filename}', f'_{a}/{filename}')
            shutil.copyfile(task_file, target_file)

        stats[num_arms] += 1

    print(f'Success: {sum(stats.values())}')
    for i in range(4):
        print(f'{i+1}: {stats[i+1]}')
    


