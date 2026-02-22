import json
from pathlib import Path

if __name__ == "__main__":
    task_files = list(Path('tasks/base_test/').rglob('*.json'))
    
    i=0
    for task_file in task_files:
        task_data = json.load(open(task_file))
        task_data['hehe'] = 3
        with open(f"test/{i}.json", "w") as f:
            json.dump(task_data, f, indent=4)
            
        i+=1