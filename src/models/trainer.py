"""
Model training pipeline for ScamGuard.

Trains and tracks:
  - Logistic Regression (baseline)
  - Random Forest
  - Gradient Boosting
  - Voting Ensemble (final model)

All experiments tracked with MLflow.
"""

import json
import time
from pathlib import Path
from typing import Any

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

from src.data.preprocessor import preprocess_dataframe
from src.features.feature_engineering import build_feature_pipeline
from src.utils.config import get_config, get_project_root
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _build_classifier_pipeline(
    classifier,
    config: dict | None = None,
) -> Pipeline:
    """Wrap a classifier with the feature pipeline into a full sklearn Pipeline."""
    feature_pipeline = build_feature_pipeline(config)
    return Pipeline(
        [
            ("features", feature_pipeline),
            ("classifier", classifier),
        ]
    )


def _get_estimators(cfg: dict) -> list[tuple[str, Any]]:
    """Create base estimator instances from config."""
    lr_cfg = cfg["models"]["logistic_regression"]
    rf_cfg = cfg["models"]["random_forest"]
    gb_cfg = cfg["models"]["gradient_boosting"]

    lr = LogisticRegression(
        C=lr_cfg["C"],
        max_iter=lr_cfg["max_iter"],
        class_weight=lr_cfg["class_weight"],
        solver=lr_cfg["solver"],
        random_state=42,
    )
    rf = RandomForestClassifier(
        n_estimators=rf_cfg["n_estimators"],
        max_depth=rf_cfg["max_depth"] or None,
        class_weight=rf_cfg["class_weight"],
        n_jobs=rf_cfg["n_jobs"],
        random_state=rf_cfg["random_state"],
    )
    gb = GradientBoostingClassifier(
        n_estimators=gb_cfg["n_estimators"],
        learning_rate=gb_cfg["learning_rate"],
        max_depth=gb_cfg["max_depth"],
        random_state=gb_cfg["random_state"],
    )
    return [("lr", lr), ("rf", rf), ("gb", gb)]


def train_single_model(
    name: str,
    classifier,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    experiment_id: str,
    cfg: dict,
) -> tuple[Pipeline, float, str]:
    """
    Train a single model and log to MLflow.

    Returns:
        (fitted_pipeline, val_accuracy, mlflow_run_id)
    """
    logger.info(f"Training model: {name}")

    with mlflow.start_run(experiment_id=experiment_id, run_name=name) as run:
        # Log parameters
        mlflow.log_params(
            {
                "model_name": name,
                "train_samples": len(train_df),
                "val_samples": len(val_df),
                "tfidf_max_features": cfg["features"]["tfidf"]["max_features"],
                "ngram_range": str(cfg["features"]["tfidf"]["ngram_range"]),
            }
        )

        # Build and train
        pipeline = _build_classifier_pipeline(classifier, cfg["features"])

        start = time.time()
        pipeline.fit(train_df, train_df["label"])
        train_time = time.time() - start

        # Evaluate
        from src.models.evaluator import compute_metrics

        val_preds = pipeline.predict(val_df)
        val_proba = (
            pipeline.predict_proba(val_df)
            if hasattr(pipeline, "predict_proba")
            else None
        )

        metrics = compute_metrics(val_df["label"].values, val_preds, val_proba)

        # Log metrics
        mlflow.log_metrics(
            {
                "val_accuracy": metrics["accuracy"],
                "val_precision_weighted": metrics["precision_weighted"],
                "val_recall_weighted": metrics["recall_weighted"],
                "val_f1_weighted": metrics["f1_weighted"],
                "train_time_seconds": train_time,
            }
        )
        if "auc_roc_weighted" in metrics:
            mlflow.log_metrics({"val_auc_roc": metrics["auc_roc_weighted"]})

        # Log model artifact
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path=f"model_{name}",
            registered_model_name=None,
        )

        logger.info(
            f"{name} — val_accuracy={metrics['accuracy']:.4f}, "
            f"f1_weighted={metrics['f1_weighted']:.4f}, "
            f"train_time={train_time:.1f}s"
        )
        return pipeline, metrics["accuracy"], run.info.run_id


def train_voting_ensemble(
    estimators: list[tuple[str, Any]],
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    experiment_id: str,
    cfg: dict,
) -> tuple[Pipeline, float, str]:
    """
    Train VotingClassifier ensemble and log to MLflow.

    Each estimator is wrapped in its own feature pipeline so they
    receive the same input DataFrame format.
    """
    logger.info("Training VotingClassifier ensemble...")

    # Build individual pipelines for each estimator
    pipeline_estimators = []
    for name, clf in estimators:
        pipe = _build_classifier_pipeline(clf, cfg["features"])
        pipeline_estimators.append((name, pipe))

    voting_cfg = cfg["models"]["voting"]
    voter = VotingClassifier(
        estimators=pipeline_estimators,
        voting=voting_cfg["voting"],
        weights=voting_cfg.get("weights"),
        n_jobs=1,
    )

    with mlflow.start_run(
        experiment_id=experiment_id, run_name="voting_ensemble"
    ) as run:
        mlflow.log_params(
            {
                "model_name": "VotingClassifier",
                "voting": voting_cfg["voting"],
                "weights": str(voting_cfg.get("weights")),
                "n_estimators": len(estimators),
                "train_samples": len(train_df),
                "val_samples": len(val_df),
            }
        )

        start = time.time()
        voter.fit(train_df, train_df["label"])
        train_time = time.time() - start

        from src.models.evaluator import compute_metrics

        val_preds = voter.predict(val_df)
        val_proba = voter.predict_proba(val_df)
        metrics = compute_metrics(val_df["label"].values, val_preds, val_proba)

        mlflow.log_metrics(
            {
                "val_accuracy": metrics["accuracy"],
                "val_precision_weighted": metrics["precision_weighted"],
                "val_recall_weighted": metrics["recall_weighted"],
                "val_f1_weighted": metrics["f1_weighted"],
                "val_auc_roc": metrics.get("auc_roc_weighted", 0),
                "train_time_seconds": train_time,
            }
        )

        # Register best model
        mlflow.sklearn.log_model(
            voter,
            artifact_path="voting_ensemble",
            registered_model_name=cfg["mlflow"]["registered_model_name"],
        )

        logger.info(
            f"Ensemble — val_accuracy={metrics['accuracy']:.4f}, "
            f"f1_weighted={metrics['f1_weighted']:.4f}, "
            f"auc_roc={metrics.get('auc_roc_weighted', 0):.4f}"
        )
        return voter, metrics["accuracy"], run.info.run_id


def run_training_pipeline(
    train_path: str | None = None,
    val_path: str | None = None,
    model_output_dir: str | None = None,
) -> dict:
    """
    Full training pipeline: load data → preprocess → train all models → save best.

    Args:
        train_path: Path to train CSV (defaults to config)
        val_path: Path to val CSV (defaults to config)
        model_output_dir: Directory to save model artifacts

    Returns:
        Dict with best model metrics and paths
    """
    cfg = get_config()
    root = get_project_root()

    # Setup paths
    if train_path is None:
        train_path = root / cfg["paths"]["data_processed"] / cfg["data"]["train_file"]
    if val_path is None:
        val_path = root / cfg["paths"]["data_processed"] / cfg["data"]["val_file"]
    if model_output_dir is None:
        model_output_dir = root / cfg["paths"]["models"]

    Path(model_output_dir).mkdir(parents=True, exist_ok=True)

    # Setup MLflow
    mlflow.set_tracking_uri((root / cfg["mlflow"]["tracking_uri"]).resolve().as_uri())
    experiment = mlflow.set_experiment(cfg["mlflow"]["experiment_name"])
    experiment_id = experiment.experiment_id
    logger.info(
        f"MLflow experiment: '{cfg['mlflow']['experiment_name']}' (id={experiment_id})"
    )

    # Load data
    logger.info("Loading training data...")
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)

    # Preprocess (add text_clean + signal features)
    from src.data.preprocessor import ThaiTextPreprocessor, preprocess_dataframe

    preprocessor = ThaiTextPreprocessor(
        remove_stopwords=cfg["preprocessing"]["remove_stopwords"],
        engine=cfg["preprocessing"]["thai_engine"],
    )
    train_df = preprocess_dataframe(train_df, preprocessor=preprocessor)
    val_df = preprocess_dataframe(val_df, preprocessor=preprocessor)

    # Get estimators
    estimators = _get_estimators(cfg)

    # Train individual models
    results = {}
    best_accuracy = 0.0
    best_pipeline = None

    for name, clf in estimators:
        pipeline, acc, run_id = train_single_model(
            name, clf, train_df, val_df, experiment_id, cfg
        )
        results[name] = {"accuracy": acc, "run_id": run_id}
        if acc > best_accuracy:
            best_accuracy = acc
            best_pipeline = pipeline

    # Train ensemble (always the final model)
    ensemble, ens_acc, ens_run_id = train_voting_ensemble(
        estimators, train_df, val_df, experiment_id, cfg
    )
    results["voting_ensemble"] = {"accuracy": ens_acc, "run_id": ens_run_id}

    # Save final model locally
    final_model_path = Path(model_output_dir) / "best_model.joblib"
    joblib.dump(ensemble, final_model_path)

    # Save metadata
    metadata = {
        "model_name": "VotingClassifier",
        "version": cfg["project"]["version"],
        "trained_at": pd.Timestamp.now().isoformat(),
        "val_accuracy": ens_acc,
        "train_samples": len(train_df),
        "val_samples": len(val_df),
        "label_names": cfg["data"]["label_names"],
        "mlflow_run_id": ens_run_id,
        "model_path": str(final_model_path),
        "all_results": results,
    }
    metadata_path = Path(model_output_dir) / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.info(f"Best model saved to: {final_model_path}")
    logger.info(f"Model metadata saved to: {metadata_path}")
    logger.info(
        f"All results: {json.dumps({k: v['accuracy'] for k, v in results.items()}, indent=2)}"
    )

    return metadata


if __name__ == "__main__":
    result = run_training_pipeline()
    print(f"\nTraining complete! Ensemble val_accuracy={result['val_accuracy']:.4f}")
