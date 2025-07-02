import os
from pathlib import Path
from threading import Thread
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv
from scripts.data_generator import generate_data

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_LOCAL_DIR = os.path.join(Path(ROOT_DIR).parent.absolute(), 'dataset')
PARALLEL_INVOCATION = True


if __name__ == "__main__":
    data = pd.read_csv(f"{DATASET_LOCAL_DIR}/creditcard.csv", delimiter=',')

    nonfrauds, frauds = data.groupby('Class').size()
    print('Number of frauds: ', frauds)
    print('Number of non-frauds: ', nonfrauds)
    print('Percentage of fradulent data:', 100.*frauds/(frauds + nonfrauds))

    feature_columns = data.columns[:-1]
    label_column = data.columns[-1]

    features = data[feature_columns].values.astype('float32')
    labels = (data[label_column].values).astype('float32')

    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )

    if PARALLEL_INVOCATION:
        # multiple simulations in parallel
        threads = []
        for i in range(10):
            thread = Thread(target=generate_data, args=(np.copy(X_test), 100_000))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        print("All simulations completed.")
    else:
        # one simulation at a time
        generate_data(np.copy(X_test), max_requests=100_000)  # Adjust max_requests as needed



