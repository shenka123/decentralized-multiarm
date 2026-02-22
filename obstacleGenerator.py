import ray
import numpy as np
from environment.rrt import RRTWrapper
from environment.tasks import Task
from tqdm import tqdm
import json
import sys
import os
import itertools

def iter_json_files(root):
    with os.scandir(root) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                yield from iter_json_files(entry.path)
            elif entry.name.endswith('.json'):
                yield entry.path

def build_obstacles(task_data, obs_config):
    """Sample a random obstacle configuration for a task."""
    obstacles_count = int(np.random.choice(np.arange(0, 6), p=[.05, .3, .3, .2, .1, .05]))
    obstacles = {}

    for obs in list(obs_config)[:obstacles_count]:
        base_poses = [b[0] for b in task_data['base_poses']]
        base = base_poses[np.random.randint(0, len(base_poses))]

        r = np.random.uniform(0.2, 0.7)
        a = np.random.uniform(0, 2 * np.pi)
        b = np.random.uniform(0, np.pi)
        offset = [
            r * np.cos(a) * np.cos(b),
            r * np.sin(a) * np.cos(b),
            r * np.sin(b)
        ]

        obstacles[obs] = [base[i] + offset[i] for i in range(3)]

    return obstacles, obstacles_count


def build_task(task_data, task_file, obstacles):
    return Task(
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

def dump_json(dics, filename):
    with open(filename, "w") as f:
        json.dump(dics, f, indent=4)


def generate_expert_demonstrations(task_name='', target_name='', config_file='', 
        reset=False, max_attempts=10, num_workers=10, ray_timeout=90, gui=False):

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
    
    # Create output directory if needed
    for dir in [experts_dir, target_dir, 'logs/']:
        if not os.path.exists(dir):
            os.makedirs(dir)

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
       
    
    # Creating workers
    workers = [
        RRTWrapper.remote(env_config=env_config, gui=gui)
        for _ in range(num_workers)
    ]
    worker_cycle = itertools.cycle(workers)


    # Pending tasks
    futures = {}
    
    for task_file in iter_json_files(tasks_dir):
        filename = os.path.basename(task_file)
        if filename in logs["runs"]:
            continue
        try:
            with open(task_file) as f:
                task_data = json.load(f)
            obstacles, obstacles_count = build_obstacles(task_data, obs_config)
            task = build_task(task_data, task_file, obstacles)
            worker = next(worker_cycle)
            future = worker.birrt_from_task.remote(task)
            futures[future] = (filename, task_data, task_file, 1, obstacles, obstacles_count)
        except Exception as e:
            print(f"[ERROR] Could not submit {filename}: {e}")
            logs["runs"][filename] = "error:0"
            logs["stats"]["processed"] += 1
            logs["stats"]["errors"] += 1

    
    total = len(futures)
    done_count = 0

        # ── Collect results as they complete ──────
    while futures:
        # Wait for at least one future to finish (with a timeout so we can
        # detect hangs and cancel them).
        ready, _ = ray.wait(
            list(futures.keys()),
            num_returns=1,
            timeout=ray_timeout
        )

        # ── Handle timed-out futures ──────────
        if not ready:
            # No future finished within ray_timeout — find the oldest one and
            # treat it as a timeout so we can retry or give up.
            future = next(iter(futures))
            filename, task_data, task_file, attempt, obstacles, obstacles_count = futures.pop(future)
            ray.cancel(future, force=True)
            waypoints = None
        else:
            future = ready[0]
            filename, task_data, task_file, attempt, obstacles, obstacles_count = futures.pop(future)
            try:
                waypoints = ray.get(future, timeout=ray_timeout)
            except ray.exceptions.GetTimeoutError:
                print(f"[TIMEOUT] {filename} attempt {attempt}/{max_attempts}")
                waypoints = None
            except Exception as e:
                print(f"[ERROR]   {filename}: {e}")
                logs["runs"][filename] = "error:0"
                logs["stats"]["processed"] += 1
                logs["stats"]["errors"] += 1
                dump_json(logs, logs_file)
                continue

        # ── Success ───────────────────────────
        if waypoints is not None and len(waypoints) > 0:
            task_data['obstacles'] = obstacles
            task_data['obstacles_count'] = obstacles_count
            dump_json(task_data, target_dir + filename)

            task = build_task(task_data, task_file, obstacles)
            output_path = f'{experts_dir}/{task.id}.npy'
            np.save(output_path, waypoints)

            logs["runs"][filename] = f"success:{attempt}"
            logs["stats"]["processed"] += 1
            logs["stats"]["success"] += 1
            dump_json(logs, logs_file)

        # ── Failure: retry or give up ─────────
        else:
            if attempt < max_attempts:
                # Resample obstacles and resubmit
                new_obstacles, new_obstacles_count = build_obstacles(task_data, obs_config)
                new_task = build_task(task_data, task_file, new_obstacles)
                worker = next(worker_cycle)
                new_future = worker.birrt_from_task.remote(new_task)
                futures[new_future] = (filename, task_data, task_file,
                                       attempt + 1, new_obstacles, new_obstacles_count)
            else:
                logs["runs"][filename] = f"failed:{attempt}"
                logs["stats"]["processed"] += 1
                logs["stats"]["failed"] += 1
                done_count += 1
                dump_json(logs, logs_file)
                print(f"[FAILED]  {filename} after {attempt} attempts — {done_count}/{total}")

    # ── Summary ───────────────────────────────
    s = logs["stats"]
    print(f"\nDone! processed={s['processed']}  "
          f"success={s['success']}  failed={s['failed']}  errors={s['errors']}")
    ray.shutdown()

    # # Process each task
    # for task_file in iter_json_files(tasks_dir):
    #     filename = os.path.basename(task_file)

    #     if filename in logs["runs"].keys():
    #         continue

        
    #     try:
    #     # Load task data
    #         with open(task_file) as f:
    #             task_data = json.load(f)
            
    #         attempt = 1
    #         obstacles_count = int(np.random.choice(np.arange(0,6), p=[.05, .3, .3, .2, .1, .05]))

    #         while True:

    #             # create obstacles config
                
    #             obstacles = {}
    #             for obs in list(obs_config)[:obstacles_count]:
    #                 # random select 1 robot base poses
    #                 base_poses = [b[0] for b in task_data['base_poses']]
    #                 base = base_poses[np.random.randint(0, len(base_poses))]

    #                 # offset in 3D polar coordinates (r, a, b)
    #                 r = np.random.uniform(0.2, 0.7)
    #                 a = np.random.uniform(0, 2*np.pi)
    #                 b = np.random.uniform(0, np.pi)
    #                 offset = [
    #                     r*np.cos(a)*np.cos(b),
    #                     r*np.sin(a)*np.cos(b),
    #                     r*np.sin(b)
    #                 ]

    #                 # set obstacle coordinate
    #                 obstacles[obs] = [base[i] + offset[i] for i in range(3)]


    #             # Create Task object
    #             task = Task(
    #                 target_eff_poses=task_data['target_eff_poses'],
    #                 base_poses=task_data['base_poses'],
    #                 start_config=task_data['start_config'],
    #                 goal_config=task_data['goal_config'],
    #                 start_goal_config=task_data.get('goal_config'),
    #                 obstacles=obstacles,
    #                 difficulty=task_data.get('difficulty', 0.0),
    #                 dynamic_speed=task_data.get('dynamic_speed'),
    #                 task_path=str(task_file)
    #             )
                
        
    #             # Generate expert waypoints using RRT
    #             waypoints = ray.get(RRTWrapper.birrt_from_task.remote(task))
                
    #             if waypoints is not None and len(waypoints) > 0:

    #                 # Save modified task
    #                 task_data['obstacles'] = obstacles
    #                 task_data['obstacles_count'] = obstacles_count

    #                 dump_json(task_data, target_dir + filename)


    #                 # Save waypoints
    #                 output_path = f'{experts_dir}{task.id}.npy'
    #                 np.save(output_path, waypoints)
                    
    #                 # Save logs
    #                 logs["runs"][filename] = f"success:{attempt}"
    #                 logs["stats"]["processed"]+=1
    #                 logs["stats"]["success"]+=1

    #                 dump_json(logs, logs_file)
                    
    #                 break
                
    #             else:  

    #                 if attempt == max_attempts:
    #                     # Save logs
    #                     logs["runs"][filename] = f"failed:{attempt}"
    #                     logs["stats"]["processed"]+=1
    #                     logs["stats"]["failed"]+=1
                        
    #                     dump_json(logs, logs_file)

    #                     break

    #                 attempt+=1

                
    #     except Exception as e:
    #         logs["runs"][filename] = "error:0"
    #         logs["stats"]["processed"]+=1
    #         logs["stats"]["errors"]+=1
    #         dump_json(logs, logs_file)

        
    
    # # Cleanup
    # ray.shutdown()
    # print("Done!")

if __name__ == "__main__":
    # Generate experts for all tasks
    
    generate_expert_demonstrations(
        task_name=sys.argv[1],
        target_name=sys.argv[2],
        reset=True,
        config_file='configs/RRTconfig.json',
        gui=False
    )