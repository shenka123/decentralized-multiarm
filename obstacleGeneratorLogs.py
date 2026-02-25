import numpy as np
import json
import sys
import os

def iter_json_files(root):
    with os.scandir(root) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                yield from iter_json_files(entry.path)
            elif entry.name.endswith('.json'):
                yield entry.path



def dump_json(dics, filename):
    with open(filename, "w") as f:
        json.dump(dics, f, indent=4)

def generate_logs(target_name = ''):
    target_dir = f'tasks/{target_name}/'
    logs_file = f'logs/birrt_{target_name}.json'

    logs = {
        "stats":{
            "processed":0,
            "success":0,
            "failed":0,
            "errors":0
        },
        "runs":{}
    }

    for task_file in iter_json_files(target_dir):
        filename = os.path.basename(task_file)
        
        logs["stats"]["processed"] += 1
        logs["stats"]["success"] += 1
        
        logs["runs"][filename] = "success:0"

    dump_json(logs, logs_file)

    

if __name__ == "__main__":
    # Generate experts for all tasks
    
    generate_logs(
        target_name=sys.argv[1]
    )