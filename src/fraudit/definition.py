# fraudit/definition.py
import os
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the configuration directory and file paths
DATASET_LOCAL_DIR = os.path.join(Path(ROOT_DIR).parent.parent.absolute(), 'dataset')
KINESIS_CONNECTOR_PATH = os.path.join(Path(ROOT_DIR).parent.absolute(), 'resources', 'spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar')
CHECKPOINT_PATH = os.path.join(Path(ROOT_DIR).parent.parent.absolute(), 'checkpoints')
print("KINESIS_CONNECTOR_PATH:", KINESIS_CONNECTOR_PATH)