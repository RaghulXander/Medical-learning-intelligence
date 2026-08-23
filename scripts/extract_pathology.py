"""
scripts/extract_pathology.py

Extracts Pathology questions from raw MedMCQA dataset splits (train, validation, test)
without modifying or discarding any questions.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path("data/raw/medmcqa")
SUBJECT_NAME = "Pathology"


def load_raw_split(file_path: Path, split_name: str) -> pd.DataFrame:
    """Loads a raw dataset file (parquet, json, jsonl, or csv) and tags the split."""
    if not file_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".parquet":
        df = pd.read_parquet(file_path)
    elif suffix in (".jsonl", ".json"):
        df = pd.read_json(file_path, lines=(suffix == ".jsonl"))
    elif suffix == ".csv":
        df = pd.read_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format for {file_path}")

    df["split"] = split_name
    return df


def extract_pathology_from_df(df: pd.DataFrame, subject: str = SUBJECT_NAME) -> pd.DataFrame:
    """Filters dataframe for questions matching subject_name case-insensitively."""
    if "subject_name" not in df.columns:
        raise KeyError("Column 'subject_name' not found in dataset.")

    mask = df["subject_name"].fillna("").astype(str).str.strip().str.lower() == subject.strip().lower()
    filtered_df = df[mask].copy()
    return filtered_df


def extract_pathology_splits(
    raw_dir: Path = DEFAULT_RAW_DIR,
    subject: str = SUBJECT_NAME,
) -> Dict[str, pd.DataFrame]:
    """
    Extracts Pathology questions from all available splits in raw_dir.
    Returns a dictionary with keys 'train', 'validation', 'test', and 'all'.
    """
    splits_files = {
        "train": raw_dir / "train.parquet",
        "validation": raw_dir / "validation.parquet",
        "test": raw_dir / "test.parquet",
    }

    extracted_splits: Dict[str, pd.DataFrame] = {}
    all_dfs = []

    for split_name, file_path in splits_files.items():
        if file_path.exists():
            raw_df = load_raw_split(file_path, split_name)
            pathology_df = extract_pathology_from_df(raw_df, subject)
            extracted_splits[split_name] = pathology_df
            all_dfs.append(pathology_df)
            logger.info(
                f"Split '{split_name}': Extracted {len(pathology_df)} {subject} questions "
                f"out of {len(raw_df)} total ({len(pathology_df)/len(raw_df)*100:.2f}%)"
            )
        else:
            logger.warning(f"File {file_path} does not exist. Skipping split '{split_name}'.")

    if all_dfs:
        extracted_splits["all"] = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"Total extracted {subject} questions across all splits: {len(extracted_splits['all'])}")
    else:
        extracted_splits["all"] = pd.DataFrame()

    return extracted_splits


def main():
    parser = argparse.ArgumentParser(description="Extract Pathology questions from MedMCQA")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="Path to raw MedMCQA files")
    parser.add_argument("--subject", type=str, default=SUBJECT_NAME, help="Subject name to extract")
    args = parser.parse_args()

    extract_pathology_splits(raw_dir=args.raw_dir, subject=args.subject)


if __name__ == "__main__":
    main()
