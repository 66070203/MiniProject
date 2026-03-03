"""
Data ingestion module for ScamGuard.

Handles loading, translating (approximate), and merging of:
  1. UCI SMS Spam Collection (English → Thai approximate mapping)
  2. Synthetic Thai dataset

Outputs a unified dataset split into train/val/test sets.
"""

import hashlib
import io
import re
import urllib.request
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.utils.config import get_config, get_project_root
from src.utils.logger import get_logger

from .generator import save_synthetic_dataset

logger = get_logger(__name__)

UCI_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases"
    "/00228/smsspamcollection.zip"
)

# Simple English → Thai keyword mapping for common spam indicators
# (Used as fallback when translation API is unavailable)
EN_SPAM_KEYWORDS_TO_TH = {
    "free": "ฟรี",
    "won": "ชนะ",
    "winner": "ผู้ชนะ",
    "prize": "รางวัล",
    "claim": "รับรางวัล",
    "cash": "เงินสด",
    "urgent": "ด่วน",
    "call now": "โทรเดี๋ยวนี้",
    "limited": "จำนวนจำกัด",
    "selected": "ได้รับการเลือก",
    "congratulations": "ยินดีด้วย",
    "click": "กด",
    "link": "ลิงก์",
}


def _translate_approximate(text: str) -> str:
    """
    Apply approximate English-to-Thai keyword replacement.
    This is a deterministic fallback when no translation API is available.
    Preserves numbers, URLs, and phone numbers; replaces key English spam words.
    """
    for en, th in EN_SPAM_KEYWORDS_TO_TH.items():
        text = re.sub(rf"\b{en}\b", th, text, flags=re.IGNORECASE)
    return text


def download_uci_dataset(raw_dir: Path) -> Path | None:
    """
    Attempt to download the UCI SMS Spam Collection zip file.

    Returns path to extracted TSV file, or None if download fails.
    """
    import zipfile

    dest_zip = raw_dir / "smsspamcollection.zip"
    dest_tsv = raw_dir / "SMSSpamCollection"

    if dest_tsv.exists():
        logger.info(f"UCI dataset already exists at {dest_tsv}")
        return dest_tsv

    logger.info("Attempting to download UCI SMS Spam Collection...")
    try:
        urllib.request.urlretrieve(UCI_URL, dest_zip)
        with zipfile.ZipFile(dest_zip, "r") as zf:
            zf.extractall(raw_dir)
        dest_zip.unlink(missing_ok=True)
        logger.info("UCI dataset downloaded and extracted successfully.")
        return dest_tsv
    except Exception as exc:
        logger.warning(f"Could not download UCI dataset: {exc}. Will skip UCI data.")
        return None


def load_uci_dataset(raw_dir: Path) -> pd.DataFrame | None:
    """
    Load UCI SMS Spam Collection and convert to unified format.

    Maps UCI labels: 'ham' → 0, 'spam' → 1
    Applies approximate Thai translation to increase linguistic diversity.
    """
    tsv_path = download_uci_dataset(raw_dir)
    if tsv_path is None or not tsv_path.exists():
        logger.warning("UCI dataset not available. Continuing without it.")
        return None

    df = pd.read_csv(tsv_path, sep="\t", header=None, names=["label_name", "text"])
    df = df.dropna(subset=["text"])

    # Map labels: UCI has only ham/spam (no phishing class)
    label_map = {"ham": 0, "spam": 1}
    df["label"] = df["label_name"].map(label_map)
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    # Apply approximate translation
    df["text"] = df["text"].apply(_translate_approximate)

    import random
    import uuid
    from datetime import datetime, timedelta

    random.seed(42)
    start = datetime(2022, 1, 1)
    df["message_id"] = [str(uuid.uuid4()) for _ in range(len(df))]
    df["source"] = "uci_sms_spam"
    df["created_at"] = [
        (start + timedelta(days=random.randint(0, 730))).strftime("%Y-%m-%d %H:%M:%S")
        for _ in range(len(df))
    ]

    df = df[["message_id", "text", "label", "label_name", "source", "created_at"]]
    logger.info(
        f"Loaded UCI dataset: {len(df)} records. Labels: {df['label_name'].value_counts().to_dict()}"
    )
    return df


def load_synthetic_dataset(raw_dir: Path, synthetic_file: str) -> pd.DataFrame:
    """Load or generate the synthetic Thai dataset."""
    synthetic_path = raw_dir / synthetic_file
    if not synthetic_path.exists():
        logger.info("Synthetic dataset not found. Generating...")
        save_synthetic_dataset(synthetic_path)
    df = pd.read_csv(synthetic_path, encoding="utf-8-sig")
    logger.info(f"Loaded synthetic dataset: {len(df)} records.")
    return df


def merge_datasets(*dfs: pd.DataFrame) -> pd.DataFrame:
    """Concatenate and deduplicate multiple datasets."""
    combined = pd.concat([df for df in dfs if df is not None], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["text"])
    after = len(combined)
    if before != after:
        logger.info(f"Removed {before - after} duplicate messages.")
    combined = combined.reset_index(drop=True)
    logger.info(
        f"Merged dataset: {len(combined)} records. "
        f"Label distribution:\n{combined['label_name'].value_counts().to_string()}"
    )
    return combined


def split_dataset(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Stratified split into train / validation / test sets.

    Args:
        df: Full dataset with 'label' column
        train_ratio: Fraction for training (default 0.70)
        val_ratio: Fraction for validation (default 0.15)
        random_state: Seed for reproducibility

    Returns:
        Tuple of (train_df, val_df, test_df)
    """
    test_ratio = 1.0 - train_ratio - val_ratio

    train_df, temp_df = train_test_split(
        df,
        test_size=(1.0 - train_ratio),
        stratify=df["label"],
        random_state=random_state,
    )
    val_df, test_df = train_test_split(
        temp_df,
        test_size=(test_ratio / (val_ratio + test_ratio)),
        stratify=temp_df["label"],
        random_state=random_state,
    )

    logger.info(
        f"Split sizes — train: {len(train_df)}, val: {len(val_df)}, test: {len(test_df)}"
    )
    return train_df, val_df, test_df


def run_ingestion_pipeline(processed_dir: Path | None = None) -> dict[str, str]:
    """
    Full ingestion pipeline: load → merge → split → save.

    Returns:
        Dict with paths to saved train/val/test CSV files
    """
    config = get_config()
    root = get_project_root()

    raw_dir = root / config["paths"]["data_raw"]
    if processed_dir is None:
        processed_dir = root / config["paths"]["data_processed"]

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Load datasets
    synthetic_df = load_synthetic_dataset(raw_dir, config["data"]["synthetic_file"])
    uci_df = load_uci_dataset(raw_dir)

    # Merge
    merged = merge_datasets(synthetic_df, uci_df)

    # Split
    split_cfg = config["data"]["split"]
    train_df, val_df, test_df = split_dataset(
        merged,
        train_ratio=split_cfg["train"],
        val_ratio=split_cfg["val"],
        random_state=config["data"]["random_state"],
    )

    # Save
    paths = {}
    for name, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        path = processed_dir / config["data"][f"{name}_file"]
        df.to_csv(path, index=False, encoding="utf-8-sig")
        paths[name] = str(path)
        logger.info(f"Saved {name} set to {path}")

    return paths


if __name__ == "__main__":
    paths = run_ingestion_pipeline()
    for split, path in paths.items():
        print(f"{split}: {path}")
