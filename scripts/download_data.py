"""Download the credit-card fraud dataset locally from Kaggle.

Source: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

Requirements:
    - `kaggle` Python package (pip install kaggle)
    - Kaggle credentials available either via:
        * ~/.kaggle/kaggle.json, or
        * KAGGLE_USERNAME / KAGGLE_KEY env vars (loaded from .env)
"""

import os
import zipfile
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file (may include KAGGLE_USERNAME / KAGGLE_KEY)
load_dotenv()

KAGGLE_DATASET = "mlg-ulb/creditcardfraud"
DATASET_LOCAL_DIR = Path(__file__).resolve().parent.parent / "dataset"


def main() -> None:
    DATASET_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    target_csv = DATASET_LOCAL_DIR / "creditcard.csv"

    print(f"Dataset directory: {DATASET_LOCAL_DIR}")
    if target_csv.exists():
        print(f"Already present — skipping download: {target_csv}")
        return

    # Import after load_dotenv so KAGGLE_USERNAME / KAGGLE_KEY are picked up
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    print(f"Downloading {KAGGLE_DATASET} from Kaggle...")
    api.dataset_download_files(
        KAGGLE_DATASET,
        path=str(DATASET_LOCAL_DIR),
        quiet=False,
        unzip=False,
    )

    for zip_path in DATASET_LOCAL_DIR.glob("*.zip"):
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(DATASET_LOCAL_DIR)
        os.remove(zip_path)

    print(f"Done — dataset available at {target_csv}")


if __name__ == "__main__":
    main()
