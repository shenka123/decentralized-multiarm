import json
import random
from pathlib import Path
import torch

if __name__ == "__main__":
    
    if not torch.cuda.is_available():
        print("Using CPU")
    print("Using GPU")