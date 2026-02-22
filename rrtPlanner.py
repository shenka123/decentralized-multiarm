import ray
import numpy as np
from pathlib import Path
from environment.rrt import RRTWrapper
from environment.tasks import Task
from os.path import exists
from os import makedirs
from tqdm import tqdm
import json
import sys


def dump_json(dics, filename):
    with open(filename, "w") as f:
        json.dump(dics, f, indent=4)


def generate_expert_demonstrations(task_name='', target_name='', config_file='', 
        reset=False, max_attempts=10, gui=False):

    """
    Generate obstacles and its RRT expert waypoints for all tasks in a directory 
    
    Tasks input located in tasks/{task_name}/
    Tasks with generated obstacles output in tasks/{target_name}/
    Experts output in experts/{target_name}/
    Training logs saved in logs/birrt_{target_name}.json
    
    reset: Whether to generate from scratch (True) or continue from logs (False)
    max_attempts: set attempts to generate obstacles
    gui: Whether to visualize RRT (slow, use False for batch processing)
    """


    
    # Initialize Ray
    print("Initializing Ray...")
    ray.init()
    
    # Environment config (from configs/default.json)
    
    with open(config_file) as f:
        env_config = json.load(f)['environment']
        obs_config = env_config['obstacles']
    
    tasks_dir = f'tasks/{task_name}/'
    target_dir = f'tasks/{target_name}/'
    experts_dir = f'experts/{target_name}/'
    logs_file = f'logs/birrt_{target_name}.json'

    # Create RRT wrapper
    print("Creating RRT wrapper...")
    rrt_wrapper = RRTWrapper.remote(
        env_config=env_config,
        gui=gui
    )
    
    # Create output directory if needed
    for dir in [experts_dir, target_dir, 'logs/']:
        if not exists(dir):
            makedirs(dir)

    logs = {
        "stats":{
            "processed":0,
            "success":0,
            "failed":0,
            "errors":0
        },
        "runs":{}
    }
    
    if not reset:
        try: 
            logs = json.load(open(logs_file))
        except: 
            pass
       
    print(logs)
    
    
    # Process each task
    for task_file in Path(tasks_dir).rglob('*.json'):

        filename = task_file.name

        if filename in logs["runs"].keys():
            print("loaded", filename)
            continue

        
        try:
        # Load task data
            with open(task_file) as f:
                task_data = json.load(f)
            
            attempt = 1
            obstacles_count = int(np.random.choice(np.arange(0,6), p=[.05, .3, .3, .2, .1, .05]))

            while True:

                # create obstacles config
                
                obstacles = {}
                for obs in list(obs_config)[:obstacles_count]:
                    # random select 1 robot base poses
                    base_poses = [b[0] for b in task_data['base_poses']]
                    base = base_poses[np.random.randint(0, len(base_poses))]

                    # offset in 3D polar coordinates (r, a, b)
                    r = np.random.uniform(0.2, 0.7)
                    a = np.random.uniform(0, 2*np.pi)
                    b = np.random.uniform(0, np.pi)
                    offset = [
                        r*np.cos(a)*np.cos(b),
                        r*np.sin(a)*np.cos(b),
                        r*np.sin(b)
                    ]

                    # set obstacle coordinate
                    obstacles[obs] = [base[i] + offset[i] for i in range(3)]


                # Create Task object
                task = Task(
                    target_eff_poses=task_data['target_eff_poses'],
                    base_poses=task_data['base_poses'],
                    start_config=task_data['start_config'],
                    goal_config=task_data['goal_config'],
                    start_goal_config=task_data.get('goal_config'),
                    obstacles=obstacles,
                    difficulty=task_data.get('difficulty', 0.0),
                    dynamic_speed=task_data.get('dynamic_speed'),
                    task_path=str(task_file)
                )
                
        
                # Generate expert waypoints using RRT
                waypoints = ray.get(rrt_wrapper.birrt_from_task.remote(task))
                
                if waypoints is not None and len(waypoints) > 0:

                    # Save modified task
                    task_data['obstacles'] = obstacles
                    task_data['obstacles_count'] = obstacles_count

                    dump_json(task_data, target_dir + filename)


                    # Save waypoints
                    output_path = f'{experts_dir}/{task.id}.npy'
                    np.save(output_path, waypoints)
                    
                    # Save logs
                    logs["runs"][filename] = f"success:{attempt}"
                    logs["stats"]["processed"]+=1
                    logs["stats"]["success"]+=1

                    dump_json(logs, logs_file)
                    
                    break
                
                else:  

                    if attempt == max_attempts:
                        # Save logs
                        logs["runs"][filename] = f"failed:{attempt}"
                        logs["stats"]["processed"]+=1
                        logs["stats"]["failed"]+=1
                        
                        dump_json(logs, logs_file)

                        break

                    attempt+=1

                
        except Exception as e:
            logs["runs"][filename] = "error:0"
            logs["stats"]["processed"]+=1
            logs["stats"]["errors"]+=1
            dump_json(logs, logs_file)

        

    
    
    # Cleanup
    ray.shutdown()
    print("\nDone!")

if __name__ == "__main__":
    # Generate experts for all tasks
    
    generate_expert_demonstrations(
        task_name=sys.argv[1],
        target_name=sys.argv[2],
        reset=True,
        config_file='configs/RRTconfig.json',
        gui=False
    )