"""
omplExpertGenerator.py

Generate expert waypoint trajectories for RL training using an OMPL planner
(BIT* by default). Reads tasks (with obstacles already baked in) from
tasks/{task_name}/, plans a path from start_config -> goal_config for each
task, and saves the resulting joint-space waypoints to
experts/{target_name}/{task.id}.npy -- the same .npy format consumed by
perform_expert_actions() / RRTSupervisionEnv.load_expert_waypoints_for_task().

Unlike obstacleGenerator.py, this script does NOT sample new obstacle
placements -- it assumes the task files already have a fixed obstacle layout
(e.g. produced by obstacleGenerator.py / obstacleGeneratorNoRRT.py) and just
needs a feasible (and, with BIT*, increasingly optimal) path through it.

Progress is tracked in logs/{planner}_{target_name}.json so the script can be
safely interrupted and resumed -- just re-run with the same args, or pass
--reset to start over.

Usage:
    python omplExpertGenerator.py <task_name> <target_name> <num_workers> [options]

Examples:
    # Plan BIT* experts for tasks/obstacle_v1/, 10 parallel workers
    python omplExpertGenerator.py obstacle_v1 obstacle_v1_bitstar 10

    # Start fresh, 45s planning budget per task, 4 retries before giving up
    python omplExpertGenerator.py obstacle_v1 obstacle_v1_bitstar 10 \
        --reset --timeout 45 --max_attempts 4

Then point training at the result (note the trailing slash, since
RRTSupervisionEnv concatenates expert_root_dir + task_id + ".npy" directly):
    python main.py --mode train --name my_run \
        --config configs/obstacle_v1.json \
        --tasks_path tasks/obstacle_v1 \
        --expert_waypoints experts/obstacle_v1_bitstar/ \
        --num_processes 10

NOTE: run this from the `multiarm2` conda env (the one with the `ompl`
python bindings installed) -- same env used by benchmark.py /
job_benchmark_ompl.sh.
"""

import argparse
import json
import os

import numpy as np
import ray
from tqdm import tqdm

from environment.rrt.omplWrapper import OMPLWrapper
from environment.tasks import Task


def iter_json_files(root):
    with os.scandir(root) as it:
        for entry in it:
            if entry.is_dir(follow_symlinks=False):
                yield from iter_json_files(entry.path)
            elif entry.name.endswith('.json'):
                yield entry.path


def iter_task_paths(tasks_dir, logs):
    """Streaming generator -- only file *paths* are held in memory at once;
    the task JSON itself is only loaded once a worker is ready for it."""
    for task_file in iter_json_files(tasks_dir):
        filename = os.path.basename(task_file)
        if filename in logs["runs"]:
            continue
        yield filename, task_file


def dump_json(dics, filename, atomic=True):
    """Write JSON, optionally via a temp file + os.replace for write
    atomicity (matches the convention used elsewhere in this repo)."""
    if atomic:
        temp_filename = 'temp/' + os.path.basename(filename)
        os.makedirs('temp/', exist_ok=True)
        with open(temp_filename, "w") as f:
            json.dump(dics, f, indent=4)
        os.replace(temp_filename, filename)
    else:
        with open(filename, "w") as f:
            json.dump(dics, f, indent=4)


def generate_experts(
        task_name,
        target_name,
        config_file='configs/RRTconfig.json',
        planner_name='BITstar',
        timeout=30.0,
        max_attempts=3,
        num_workers=10,
        reset=False,
        gui=False):

    tasks_dir = f'tasks/{task_name}/'
    experts_dir = f'experts/{target_name}/'
    logs_file = f'logs/{planner_name.lower()}_{target_name}.json'

    if not os.path.exists(tasks_dir):
        print(f"[ERROR] tasks dir not found: {tasks_dir}")
        return

    if gui and num_workers > 1:
        print("[WARN] --gui with num_workers > 1 will try to open "
              "multiple GUI windows. Consider --num_workers 1 with --gui.")

    with open(config_file) as f:
        env_config = json.load(f)['environment']

    logs = {
        "stats": {"processed": 0, "success": 0, "failed": 0, "errors": 0},
        "runs": {}
    }
    if not reset:
        try:
            logs = json.load(open(logs_file))
            print(f"[Resume] Loaded {len(logs['runs'])} prior "
                  f"results from {logs_file}")
        except Exception:
            pass

    for d in [experts_dir, 'logs/', 'temp/']:
        os.makedirs(d, exist_ok=True)

    total_tasks = sum(1 for _ in iter_json_files(tasks_dir))
    print(f"Found {total_tasks} task files in {tasks_dir}")

    print("Initializing Ray...")
    ray.init()

    print(f"Creating {num_workers} OMPLWrapper ({planner_name}) workers...")
    workers = [
        OMPLWrapper.remote(
            env_config=env_config, gui=gui, planner_name=planner_name)
        for _ in range(num_workers)
    ]

    pending = iter_task_paths(tasks_dir, logs)
    worker_state = {}
    done_count = 0
    pbar = tqdm(total=total_tasks, initial=len(logs["runs"]),
                dynamic_ncols=True, smoothing=0.05)

    def already_done(task_id):
        return os.path.exists(os.path.join(experts_dir, f'{task_id}.npy'))

    def assign_next_task(worker):
        while True:
            try:
                filename, task_file = next(pending)
            except StopIteration:
                return False

            task = Task.from_file(task_file)
            if task is None:
                logs["runs"][filename] = "error:0"
                logs["stats"]["processed"] += 1
                logs["stats"]["errors"] += 1
                pbar.update(1)
                continue

            # belt-and-suspenders: if the npy already exists (e.g. logs
            # were lost/reset but outputs weren't), don't replan it.
            if not reset and already_done(task.id):
                logs["runs"][filename] = "success:0"
                logs["stats"]["processed"] += 1
                logs["stats"]["success"] += 1
                pbar.update(1)
                continue

            future = worker.plan_from_task.remote(task, timeout=timeout)
            worker_state[worker] = {
                "future": future,
                "filename": filename,
                "task": task,
                "attempt": 1,
            }
            return True

    def retry_same_worker(worker):
        state = worker_state[worker]
        state["future"] = worker.plan_from_task.remote(
            state["task"], timeout=timeout)
        state["attempt"] += 1

    for worker in workers:
        if not assign_next_task(worker):
            break

    # BIT* can spend up to `timeout` solving + timeout/2 simplifying,
    # so give generous headroom over the planner's own internal timeout.
    ray_timeout = timeout * 1.5 + 30

    while worker_state:
        if done_count % 50 == 0:
            dump_json(logs, logs_file)

        all_futures = [s["future"] for s in worker_state.values()]
        future_to_worker = {s["future"]: w for w, s in worker_state.items()}

        ready, _ = ray.wait(all_futures, num_returns=1, timeout=ray_timeout)

        if not ready:
            future = all_futures[0]
            worker = future_to_worker[future]
            ray.cancel(future, force=True)
            waypoints = None
        else:
            future = ready[0]
            worker = future_to_worker[future]
            try:
                waypoints = ray.get(future, timeout=5)
            except Exception as e:
                state = worker_state[worker]
                print(f"\n[ERROR] Could not get result for "
                      f"{state['filename']}: {e}")
                logs["runs"][state["filename"]] = "error:0"
                logs["stats"]["processed"] += 1
                logs["stats"]["errors"] += 1
                done_count += 1
                pbar.update(1)
                del worker_state[worker]
                assign_next_task(worker)
                continue

        state = worker_state[worker]
        filename = state["filename"]
        task = state["task"]
        attempt = state["attempt"]

        if waypoints is not None and len(waypoints) > 0:
            np.save(os.path.join(experts_dir, f'{task.id}.npy'),
                    np.array(waypoints))
            logs["runs"][filename] = f"success:{attempt}"
            logs["stats"]["processed"] += 1
            logs["stats"]["success"] += 1
            done_count += 1
            pbar.update(1)
            pbar.set_description(
                f'success={logs["stats"]["success"]} '
                f'failed={logs["stats"]["failed"]}')
            del worker_state[worker]
            assign_next_task(worker)
        else:
            if attempt < max_attempts:
                retry_same_worker(worker)
            else:
                logs["runs"][filename] = f"failed:{attempt}"
                logs["stats"]["processed"] += 1
                logs["stats"]["failed"] += 1
                done_count += 1
                pbar.update(1)
                del worker_state[worker]
                assign_next_task(worker)

    pbar.close()
    dump_json(logs, logs_file)

    s = logs["stats"]
    print(f"\nDone! processed={s['processed']}  success={s['success']}  "
          f"failed={s['failed']}  errors={s['errors']}")
    if s["processed"] > 0:
        print(f"Success rate: {s['success'] / s['processed'] * 100:.1f}%")
    print(f"Waypoints written to: {experts_dir}")
    print("When training/supervising, point to them with "
          "(note the trailing slash):")
    print(f"  --expert_waypoints {experts_dir}")

    ray.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate OMPL-planned expert waypoints for RL training.")
    parser.add_argument("task_name",
                        help="source dir name under tasks/ "
                             "(tasks must already have obstacles baked in)")
    parser.add_argument("target_name",
                        help="output dir name under experts/")
    parser.add_argument("num_workers", type=int,
                        help="number of parallel OMPL planning workers")
    parser.add_argument("--planner", default="BITstar",
                        choices=["RRTConnect", "RRT", "BITstar",
                                 "PRM", "LBKPIECE"],
                        help="OMPL planner to use (default: BITstar)")
    parser.add_argument("--config", default="configs/RRTconfig.json",
                        help="env config json (obstacles/max_ur5s_count/etc)")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="per-task planning time budget in seconds")
    parser.add_argument("--max_attempts", type=int, default=3,
                        help="re-plan attempts before marking a task failed")
    parser.add_argument("--reset", action="store_true",
                        help="ignore existing logs/outputs, start fresh")
    parser.add_argument("--gui", action="store_true",
                        help="visualize planning (slow -- use num_workers 1)")
    args = parser.parse_args()

    generate_experts(
        task_name=args.task_name,
        target_name=args.target_name,
        config_file=args.config,
        planner_name=args.planner,
        timeout=args.timeout,
        max_attempts=args.max_attempts,
        num_workers=args.num_workers,
        reset=args.reset,
        gui=args.gui,
    )
