"""
scripts/import_medmcqa.py

Downloads raw MedMCQA dataset splits from Hugging Face if not already present locally.
Keeps raw files immutable in data/raw/medmcqa/.
"""

from __future__ import annotations

import logging
import os
import urllib.request
from pathlib import Path
from typing import Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw/medmcqa")

REMOTE_FILES: Dict[str, str] = {
    "train.parquet": "https://huggingface.co/datasets/medmcqa/resolve/main/data/train-00000-of-00001.parquet",
    "validation.parquet": "https://huggingface.co/datasets/medmcqa/resolve/main/data/validation-00000-of-00001.parquet",
    "test.parquet": "https://huggingface.co/datasets/medmcqa/resolve/main/data/test-00000-of-00001.parquet",
}


def download_medmcqa(dest_dir: Path = DEFAULT_RAW_DIR, force: bool = False) -> Dict[str, Path]:
    """
    Downloads raw MedMCQA parquet files to dest_dir.
    Returns mapping of split names to local file paths.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded_paths: Dict[str, Path] = {}

    for filename, url in REMOTE_FILES.items():
        file_path = dest_dir / filename
        if not file_path.exists() or force:
            logger.info(f"Downloading {filename} from {url}...")
            urllib.request.urlretrieve(url, file_path)
            logger.info(f"Downloaded {filename} ({file_path.stat().st_size:,} bytes).")
        else:
            logger.info(f"File {filename} already exists at {file_path} ({file_path.stat().st_size:,} bytes).")

        downloaded_paths[filename.replace(".parquet", "")] = file_path

    return downloaded_paths


if __name__ == "__main__":
    download_medmcqa()
