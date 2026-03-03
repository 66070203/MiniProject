"""
Data validation for ScamGuard datasets.

Uses pandera for schema-based validation of input DataFrames.
Checks data quality, class distribution, and text statistics.
"""

import json
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import pandera as pa
from pandera import Check, Column, DataFrameSchema

from src.utils.config import get_project_root
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

RAW_SCHEMA = DataFrameSchema(
    columns={
        "message_id": Column(str, nullable=False),
        "text": Column(
            str,
            checks=[
                Check(
                    lambda s: s.str.len() >= 5,
                    element_wise=False,
                    error="Text too short",
                ),
                Check(
                    lambda s: s.str.len() <= 1000,
                    element_wise=False,
                    error="Text too long",
                ),
                Check(lambda s: s.notna().all(), error="Text contains nulls"),
            ],
            nullable=False,
        ),
        "label": Column(
            int,
            checks=Check.isin([0, 1, 2]),
            nullable=False,
        ),
        "label_name": Column(
            str,
            checks=Check.isin(["ham", "spam", "phishing"]),
            nullable=False,
        ),
        "source": Column(str, nullable=False),
        "created_at": Column(str, nullable=False),
    },
    strict=False,  # allow extra columns
)

PROCESSED_SCHEMA = DataFrameSchema(
    columns={
        "text_clean": Column(
            str,
            checks=Check(lambda s: s.str.strip().str.len() > 0, element_wise=False),
            nullable=False,
        ),
        "label": Column(int, checks=Check.isin([0, 1, 2]), nullable=False),
        "text_length": Column(float, checks=Check.ge(0), nullable=False),
        "url_count": Column(float, checks=Check.ge(0), nullable=False),
        "phone_count": Column(float, checks=Check.ge(0), nullable=False),
    },
    strict=False,
)


class ValidationReport(NamedTuple):
    """Result of a validation check."""

    passed: bool
    n_rows: int
    label_distribution: dict
    issues: list[str]
    stats: dict


def validate_raw(df: pd.DataFrame) -> ValidationReport:
    """
    Validate raw dataset schema and quality.

    Args:
        df: Raw dataset DataFrame

    Returns:
        ValidationReport with pass/fail status and details
    """
    issues = []

    # Schema check
    try:
        RAW_SCHEMA.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        for _, row in e.failure_cases.iterrows():
            issues.append(f"Schema: {row['check']} failed on column '{row['column']}'")

    # Duplicate check
    n_dupes = df.duplicated(subset=["text"]).sum()
    if n_dupes > 0:
        issues.append(f"Found {n_dupes} duplicate messages")

    # Class imbalance check
    label_counts = df["label"].value_counts().to_dict()
    total = len(df)
    for label, count in label_counts.items():
        ratio = count / total
        if ratio > 0.80:
            issues.append(f"Class {label} dominates at {ratio:.1%}")

    # Minimum class size
    min_count = min(label_counts.values()) if label_counts else 0
    if min_count < 100:
        issues.append(f"Smallest class has only {min_count} samples (min: 100)")

    _text_lengths = df["text"].dropna().str.len()
    stats = {
        "total_rows": total,
        "avg_text_length": (
            float(_text_lengths.mean()) if len(_text_lengths) > 0 else 0.0
        ),
        "min_text_length": int(_text_lengths.min()) if len(_text_lengths) > 0 else 0,
        "max_text_length": int(_text_lengths.max()) if len(_text_lengths) > 0 else 0,
        "n_duplicates": int(n_dupes),
    }

    passed = len(issues) == 0
    if passed:
        logger.info(f"Raw validation PASSED for {total} records.")
    else:
        logger.warning(f"Raw validation found {len(issues)} issue(s): {issues}")

    return ValidationReport(
        passed=passed,
        n_rows=total,
        label_distribution={int(k): int(v) for k, v in label_counts.items()},
        issues=issues,
        stats=stats,
    )


def validate_processed(df: pd.DataFrame) -> ValidationReport:
    """
    Validate preprocessed dataset schema and feature columns.

    Args:
        df: Preprocessed DataFrame with text_clean and signal features

    Returns:
        ValidationReport
    """
    issues = []

    try:
        PROCESSED_SCHEMA.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        for _, row in e.failure_cases.iterrows():
            issues.append(f"Schema: {row['check']} on '{row['column']}'")

    # Check for empty texts
    empty_count = (df["text_clean"].str.strip().str.len() == 0).sum()
    if empty_count > 0:
        issues.append(f"{empty_count} rows have empty text_clean")

    label_counts = df["label"].value_counts().to_dict()
    total = len(df)

    stats = {
        "total_rows": total,
        "avg_clean_length": float(df["text_clean"].str.len().mean()),
        "avg_url_count": float(df["url_count"].mean()),
        "avg_phone_count": float(df["phone_count"].mean()),
        "empty_texts": int(empty_count),
    }

    passed = len(issues) == 0
    if passed:
        logger.info(f"Processed validation PASSED for {total} records.")
    else:
        logger.warning(f"Processed validation issues: {issues}")

    return ValidationReport(
        passed=passed,
        n_rows=total,
        label_distribution={int(k): int(v) for k, v in label_counts.items()},
        issues=issues,
        stats=stats,
    )


def save_schema(output_path: str | None = None) -> str:
    """
    Save the expected data schema as JSON for documentation.

    Returns:
        Path to saved schema JSON
    """
    root = get_project_root()
    if output_path is None:
        output_path = root / "data" / "schemas" / "message_schema.json"

    schema_dict = {
        "dataset": "ScamGuard Thai SMS Spam Dataset",
        "version": "1.0.0",
        "columns": {
            "message_id": {
                "type": "string",
                "nullable": False,
                "description": "Unique UUID per message",
            },
            "text": {
                "type": "string",
                "nullable": False,
                "min_length": 5,
                "max_length": 1000,
            },
            "label": {
                "type": "integer",
                "nullable": False,
                "values": [0, 1, 2],
                "encoding": {"0": "ham", "1": "spam", "2": "phishing"},
            },
            "label_name": {
                "type": "string",
                "nullable": False,
                "values": ["ham", "spam", "phishing"],
            },
            "source": {
                "type": "string",
                "nullable": False,
                "values": ["synthetic", "uci_sms_spam"],
            },
            "created_at": {"type": "string", "format": "YYYY-MM-DD HH:MM:SS"},
        },
        "processed_extra_columns": {
            "text_clean": "Preprocessed tokenized text",
            "text_length": "Length of raw text in characters",
            "word_count": "Number of words in raw text",
            "url_count": "Number of URLs detected",
            "phone_count": "Number of phone numbers detected",
            "exclamation_count": "Number of ! characters",
            "number_ratio": "Ratio of numeric characters",
            "caps_ratio": "Ratio of uppercase characters",
        },
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema_dict, f, ensure_ascii=False, indent=2)

    logger.info(f"Schema saved to: {output_path}")
    return str(output_path)
