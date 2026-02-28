import json
import random
from pathlib import Path
import torch

if __name__ == "__main__":
    
    d = 'runs/obstacle_v1/ckpt_multiarm_motion_planner_'
    a = torch.load(d + "00001")
    b = torch.load(d + "00013")

    for k in a['networks'].keys():
        for k2 in a['networks'][k]:
            if not torch.equal(a['networks'][k][k2], b['networks'][k][k2]):
                print("Different at:", k + '.' + k2)
            else:
                print(k + '.' + k2, "is equal.")
    print(a['networks'].keys())
    print(a['stats'], b['stats'])