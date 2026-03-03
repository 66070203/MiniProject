"""
Model evaluation utilities for GuardianShield.

Provides metrics computation, confusion matrix, and reporting functions.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.utils.config import get_config, get_project_root
from src.utils.logger import get_logger

logger = get_logger(__name__)

LABEL_NAMES = ["ham", "spam", "phishing"]


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
) -> dict[str, float]:
    """
    Compute comprehensive classification metrics.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        y_proba: Predicted probabilities (n_samples × n_classes), optional

    Returns:
        Dict of metric names to float values
    """
    metrics: dict[str, float] = {}

    metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
    metrics["precision_weighted"] = float(
        precision_score(y_true, y_pred, average="weighted", zero_division=0)
    )
    metrics["recall_weighted"] = float(
        recall_score(y_true, y_pred, average="weighted", zero_division=0)
    )
    metrics["f1_weighted"] = float(
        f1_score(y_true, y_pred, average="weighted", zero_division=0)
    )
    metrics["f1_macro"] = float(
        f1_score(y_true, y_pred, average="macro", zero_division=0)
    )

    # Per-class metrics
    labels = sorted(np.unique(np.concatenate([y_true, y_pred])))
    for label_idx in labels:
        label_name = (
            LABEL_NAMES[int(label_idx)]
            if int(label_idx) < len(LABEL_NAMES)
            else str(label_idx)
        )
        mask = y_true == label_idx
        if mask.sum() > 0:
            metrics[f"precision_{label_name}"] = float(
                precision_score(
                    y_true, y_pred, labels=[label_idx], average="micro", zero_division=0
                )
            )
            metrics[f"recall_{label_name}"] = float(
                recall_score(
                    y_true, y_pred, labels=[label_idx], average="micro", zero_division=0
                )
            )
            metrics[f"f1_{label_name}"] = float(
                f1_score(
                    y_true, y_pred, labels=[label_idx], average="micro", zero_division=0
                )
            )

    # AUC-ROC (requires probabilities and multi-class)
    if y_proba is not None:
        try:
            n_classes = y_proba.shape[1]
            if n_classes >= 2:
                metrics["auc_roc_weighted"] = float(
                    roc_auc_score(
                        y_true, y_proba, multi_class="ovr", average="weighted"
                    )
                )
                metrics["auc_roc_macro"] = float(
                    roc_auc_score(y_true, y_proba, multi_class="ovr", average="macro")
                )
        except Exception as e:
            logger.warning(f"Could not compute AUC-ROC: {e}")

    return metrics


def get_classification_report(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label_names: list[str] | None = None,
) -> str:
    """Return sklearn classification report string."""
    if label_names is None:
        label_names = LABEL_NAMES
    return classification_report(
        y_true, y_pred, target_names=label_names, zero_division=0
    )


def get_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> np.ndarray:
    """Return confusion matrix as numpy array."""
    labels = list(range(len(LABEL_NAMES)))
    return confusion_matrix(y_true, y_pred, labels=labels)


def evaluate_on_test_set(
    model,
    test_path: str | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """
    Run full evaluation on the test set and save a report.

    Args:
        model: Fitted sklearn Pipeline or VotingClassifier
        test_path: Path to test CSV
        output_path: Where to save JSON evaluation report

    Returns:
        Dict with metrics, confusion matrix, and classification report
    """
    cfg = get_config()
    root = get_project_root()

    if test_path is None:
        test_path = root / cfg["paths"]["data_processed"] / cfg["data"]["test_file"]

    test_df = pd.read_csv(test_path)

    # Preprocess if text_clean not present
    if "text_clean" not in test_df.columns:
        from src.data.preprocessor import preprocess_dataframe

        test_df = preprocess_dataframe(test_df)

    y_true = test_df["label"].values
    y_pred = model.predict(test_df)
    y_proba = model.predict_proba(test_df) if hasattr(model, "predict_proba") else None

    metrics = compute_metrics(y_true, y_pred, y_proba)
    cm = get_confusion_matrix(y_true, y_pred).tolist()
    report = get_classification_report(y_true, y_pred)

    logger.info(f"\nTest Set Evaluation:\n{report}")
    logger.info(f"Test accuracy: {metrics['accuracy']:.4f}")

    result = {
        "metrics": metrics,
        "confusion_matrix": cm,
        "classification_report": report,
        "test_samples": int(len(test_df)),
        "label_names": LABEL_NAMES,
    }

    if output_path is None:
        output_path = root / cfg["paths"]["models"] / "evaluation_report.json"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info(f"Evaluation report saved to: {output_path}")

    return result
