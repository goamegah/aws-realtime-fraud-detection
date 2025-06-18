from threading import Thread
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv
from definition import DATASET_LOCAL_DIR
from data_generator import generate_data

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

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
        features, labels, test_size=0.1, random_state=42, stratify=labels
    )

    if PARALLEL_INVOCATION:
        thread = Thread(target = generate_data, args=[np.copy(X_test)])
        thread.start()
    else:
        # one simulation at a time
        generate_data(np.copy(X_test), max_requests=100)  # Adjust max_requests as needed



