"""
MLflow prediction logger for ScamGuard.

Logs each inference request as a short MLflow run inside the
dedicated "prediction_logs" experiment, keeping model-training
experiments cleanly separated from live inference telemetry.

Usage (called automatically from src/api/main.py):
    from src.utils.mlflow_logger import log_prediction_to_mlflow
    log_prediction_to_mlflow(text, result, user_id=user_id)

Tracking URI resolution (in order of priority):
    1. MLFLOW_TRACKING_URI environment variable  (Docker: http://mlflow:5000)
    2. configs/config.yaml  mlflow.tracking_uri  (local: "mlruns" directory)
"""

import os

import mlflow

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

_initialized = False


def _init_mlflow() -> None:
    """Configure MLflow tracking URI and experiment (idempotent)."""
    global _initialized
    if _initialized:
        return

    cfg = get_config()
    mlflow_cfg: dict = cfg.get("mlflow", {})

    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        mlflow_cfg.get("tracking_uri", "mlruns"),
    )
    mlflow.set_tracking_uri(tracking_uri)

    exp_name = mlflow_cfg.get("prediction_experiment", "prediction_logs")
    mlflow.set_experiment(exp_name)

    logger.info(
        f"MLflow prediction logger initialised — URI={tracking_uri}, experiment={exp_name}"
    )
    _initialized = True


def log_prediction_to_mlflow(
    text: str,
    result: dict,
    user_id: str | None = None,
) -> None:
    """
    Log one prediction as a completed MLflow run.

    Tags (searchable strings):
        label            — "ham" / "spam" / "phishing"
        risk_level       — "low" / "high"
        confidence_source — "ml" / "hybrid"
        user_id          — caller identifier (or "anonymous")
        text_preview     — first 200 chars of the input text

    Metrics (numeric, visible in MLflow charts):
        confidence        — model confidence [0–1]
        label_id          — numeric class  (0 = ham, 1 = spam, 2 = phishing)
        processing_time_ms
        prob_ham, prob_spam, prob_phishing  — class probabilities

    Params (string metadata):
        text_length      — character count of the input
        keywords_count   — number of risk keywords detected
    """
    try:
        _init_mlflow()

        with mlflow.start_run(run_name="prediction"):
            # ── Tags ──────────────────────────────────────────────────────────
            mlflow.set_tags(
                {
                    "label": result.get("label", ""),
                    "risk_level": result.get("risk_level", ""),
                    "confidence_source": result.get("confidence_source", "ml"),
                    "user_id": user_id or "anonymous",
                    "text_preview": text[:200].replace("\n", " "),
                }
            )

            # ── Metrics ───────────────────────────────────────────────────────
            probs: dict = result.get("probabilities", {})
            mlflow.log_metrics(
                {
                    "confidence": float(result.get("confidence", 0.0)),
                    "label_id": float(result.get("label_id", 0)),
                    "processing_time_ms": float(result.get("processing_time_ms", 0.0)),
                    "prob_ham": float(probs.get("ham", 0.0)),
                    "prob_spam": float(probs.get("spam", 0.0)),
                    "prob_phishing": float(probs.get("phishing", 0.0)),
                }
            )

            # ── Params ────────────────────────────────────────────────────────
            mlflow.log_params(
                {
                    "text_length": len(text),
                    "keywords_count": len(result.get("keywords", [])),
                }
            )

    except Exception as exc:
        # Never let MLflow logging break the prediction response
        logger.warning(f"MLflow prediction logging failed (non-fatal): {exc}")
