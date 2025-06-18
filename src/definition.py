import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the configuration directory and file paths
DATASET_LOCAL_DIR = os.path.join(Path(ROOT_DIR).parent.absolute(), 'dataset')
# print(DATASET_DIR)