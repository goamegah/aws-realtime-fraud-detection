import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(Path(ROOT_DIR).parent.parent.absolute(), 'dataset')
CHECKPOINTS_PATH = os.path.join(Path(ROOT_DIR).parent.parent.absolute(), 'checkpoints')


print(DATASET_PATH)