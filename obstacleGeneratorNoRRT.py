"""
obstacleGeneratorNoRRT.py

Generates and validates obstacle placements for task files WITHOUT running BiRRT.
Validation only checks that obstacles don't collide with arms at:
  - start_config
  - goal_config  (start_goal_config if present, else goal_config)

Tasks with valid obstacle placements are written to tasks/{target_name}/.
No expert waypoints are generated.

Usage:
    python obstacleGeneratorNoRRT.py <task_name> <target_name> <num_workers> [reset]

    python obstacleGeneratorNoRRT.py base obstacle_v1_nort 10
    python obstacleGeneratorNoRRT.py base obstacle_v1_nort 10 reset
"""

import ray
import numpy as np
from environment.rrt.pybullet_utils import configure_pybullet
from environment.rrt.ur5_group import UR5Group
from environment.tasks import Task
import json
import sys
import os
from itertools import chain


# ---------------------------------------------------------------------------
# Helpers shared with obstacleGenerator.py
# ---------------------------------------------------------------------------

def iter_json_files(root):
    with os.scandir(root) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                yield from iter_json_files(entry.path)
            elif entry.name.endswith('.json'):
                yield entry.path


def iter_tasks(tasks_dir, logs):
    for task_file in iter_json_files(tasks_dir):
        filename = os.path.basename(task_file)
        if filename in logs["runs"]:
            continue
        try:
            with open(task_file) as f:
                task_data = json.load(f)
            yield filename, task_data, task_file
        except Exception as e:
            print(f"[ERROR] Could not load {filename}: {e}")
            logs["runs"][filename] = "error:0"
            logs["stats"]["processed"] += 1
            logs["stats"]["errors"] += 1


def dump_json(dics, filename, save_write=False):
    if save_write:
        temp_filename = 'temp/' + os.path.basename(filename)
        if not os.path.exists('temp/'):
            os.makedirs('temp/')
        with open(temp_filename, "w") as f:
            json.dump(dics, f, indent=4)
        os.replace(temp_filename, filename)
    else:
        with open(filename, "w") as f:
            json.dump(dics, f, indent=4)


def build_obstacles(task_data, obs_config):
    """Sample a random obstacle configuration for a task (same as obstacleGenerator)."""
    obstacles_count = int(np.random.choice(
        np.arange(0, 6), p=[.1, .15, .2, .2, .2, .15]))
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


# ---------------------------------------------------------------------------
# Collision-only validator actor
# ---------------------------------------------------------------------------

@ray.remote
class CollisionValidator:
    """
    Lightweight Ray actor: one PyBullet instance used only for collision
    checking — no motion planning.
    """

    def __init__(self, env_config, gui=False):
        from environment.utils import create_ur5s, create_obstacles

        configure_pybullet(
            rendering=gui,
            debug=False,
            yaw=150, pitch=-30,
            dist=2., target=(0, 0, 0.1))

        import pybullet as p
        import pybullet_data
        p.loadURDF("plane.urdf",
                   [0, 0, -env_config['collision_distance'] - 0.01])

        self.ur5_group = UR5Group(
            create_ur5s_fn=lambda: create_ur5s(
                radius=0.8,
                count=env_config['max_ur5s_count'],
                speed=env_config['ur5_speed']),
            collision_distance=env_config['collision_distance'],
            all_obs=create_obstacles(env_config['obstacles']))

    def validate(self, task_data, obstacles):
        """
        Returns True if the given obstacle placement is collision-free with
        the arms at both start_config and goal_config.

        Validation configs checked:
          - start_config
          - start_goal_config (falling back to goal_config if absent/None)
        """
        base_poses   = task_data['base_poses']
        start_config = task_data['start_config']

        goal_config = task_data.get('start_goal_config')
        if goal_config is None or any(g is None for g in goal_config):
            goal_config = task_data['goal_config']

        obs_conf = obstacles   # dict  {obs_id: [x, y, z]}

        # --- check start config ---
        self.ur5_group.setup(
            start_poses=base_poses,
            start_joints=start_config,
            obs_conf=obs_conf)

        collision_fn = self.ur5_group.get_collision_fn()
        flat_start = list(chain.from_iterable(start_config))
        if collision_fn(flat_start):
            return False

        # --- check goal config (re-use same obstacle placement) ---
        self.ur5_group.setup(
            start_poses=base_poses,
            start_joints=goal_config,
            obs_conf=obs_conf)

        collision_fn = self.ur5_group.get_collision_fn()
        flat_goal = list(chain.from_iterable(goal_config))
        if collision_fn(flat_goal):
            return False

        return True


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------

def generate_obstacles_no_rrt(
        task_name='',
        target_name='',
        config_file='configs/RRTconfig.json',
        reset=False,
        max_attempts=10,
        num_workers=10,
        gui=False):
    """
    Generate obstacle placements that are collision-free with arm configs.
    No BiRRT / motion planning is run.

    tasks/{task_name}/     — source tasks
    tasks/{target_name}/   — output tasks with obstacle fields added
    logs/obs_{target_name}.json — progress log
    """

    print("Initialising Ray...")
    ray.init()

    with open(config_file) as f:
        env_config = json.load(f)['environment']
    obs_config = env_config['obstacles']

    tasks_dir  = f'tasks/{task_name}/'
    target_dir = f'tasks/{target_name}/'
    logs_file  = f'logs/obs_{target_name}.json'

    logs = {
        "stats": {"processed": 0, "success": 0, "failed": 0, "errors": 0},
        "runs": {}
    }
    if not reset:
        try:
            logs = json.load(open(logs_file))
        except Exception:
            pass

    for d in [target_dir, 'logs/', 'temp/']:
        os.makedirs(d, exist_ok=True)

    # ── Worker pool ────────────────────────────────────────────────────────
    print(f"Creating {num_workers} CollisionValidator workers...")
    workers = [
        CollisionValidator.remote(env_config=env_config, gui=gui)
        for _ in range(num_workers)
    ]

    # ── Task queue ─────────────────────────────────────────────────────────
    pending = iter_tasks(tasks_dir, logs)

    # worker_state: {worker: {future, filename, task_data, task_file,
    #                          attempt, obstacles, obstacles_count}}
    worker_state = {}
    done_count = 0

    def assign_next_task(worker):
        try:
            filename, task_data, task_file = next(pending)
        except StopIteration:
            return False
        obstacles, obstacles_count = build_obstacles(task_data, obs_config)
        future = worker.validate.remote(task_data, obstacles)
        worker_state[worker] = {
            "future":          future,
            "filename":        filename,
            "task_data":       task_data,
            "task_file":       task_file,
            "attempt":         1,
            "obstacles":       obstacles,
            "obstacles_count": obstacles_count,
        }
        return True

    def retry(worker):
        state = worker_state[worker]
        obstacles, obstacles_count = build_obstacles(
            state["task_data"], obs_config)
        future = worker.validate.remote(state["task_data"], obstacles)
        state["future"]          = future
        state["attempt"]        += 1
        state["obstacles"]       = obstacles
        state["obstacles_count"] = obstacles_count

    # Seed workers
    for worker in workers:
        if not assign_next_task(worker):
            break

    # ── Main loop ──────────────────────────────────────────────────────────
    while worker_state:
        if done_count % 100 == 0:
            dump_json(logs, logs_file, save_write=True)

        all_futures      = [s["future"] for s in worker_state.values()]
        future_to_worker = {s["future"]: w for w, s in worker_state.items()}

        ready, _ = ray.wait(all_futures, num_returns=1, timeout=10.0)

        if not ready:
            # Timed out — shouldn't happen for a simple collision check,
            # but handle gracefully.
            future = all_futures[0]
            worker = future_to_worker[future]
            ray.cancel(future, force=True)
            valid = False
        else:
            future = ready[0]
            worker = future_to_worker[future]
            try:
                valid = ray.get(future, timeout=5)
            except Exception as e:
                print(f"[ERROR] Ray get failed: {e}")
                state = worker_state[worker]
                logs["runs"][state["filename"]] = "error:0"
                logs["stats"]["processed"] += 1
                logs["stats"]["errors"]    += 1
                done_count += 1
                del worker_state[worker]
                assign_next_task(worker)
                continue

        state           = worker_state[worker]
        filename        = state["filename"]
        task_data       = state["task_data"]
        obstacles       = state["obstacles"]
        obstacles_count = state["obstacles_count"]
        attempt         = state["attempt"]

        if valid:
            # Write output task file with obstacle info
            task_data['obstacles']       = obstacles
            task_data['obstacles_count'] = obstacles_count
            dump_json(task_data, target_dir + filename)

            logs["runs"][filename]       = f"success:{attempt}"
            logs["stats"]["processed"] += 1
            logs["stats"]["success"]   += 1
            done_count += 1

            del worker_state[worker]
            assign_next_task(worker)

        else:
            if attempt < max_attempts:
                retry(worker)
            else:
                logs["runs"][filename]      = f"failed:{attempt}"
                logs["stats"]["processed"] += 1
                logs["stats"]["failed"]    += 1
                done_count += 1

                del worker_state[worker]
                assign_next_task(worker)

    dump_json(logs, logs_file, save_write=True)

    s = logs["stats"]
    print(f"\nDone!  processed={s['processed']}  "
          f"success={s['success']}  failed={s['failed']}  "
          f"errors={s['errors']}")
    ray.shutdown()


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    generate_obstacles_no_rrt(
        task_name=sys.argv[1],
        target_name=sys.argv[2],
        num_workers=int(sys.argv[3]),
        reset="reset" in sys.argv,
        config_file='configs/RRTconfig.json',
        gui=False,
    )