"""
Feature engineering pipeline for GuardianShield.

Combines TF-IDF text features with hand-crafted signal features
into a unified scikit-learn Pipeline-compatible transformer.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

SIGNAL_FEATURE_COLS = [
    "text_length",
    "word_count",
    "url_count",
    "phone_count",
    "exclamation_count",
    "number_ratio",
    "caps_ratio",
]


class SignalFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts pre-computed numerical signal features from a DataFrame.

    Expects the DataFrame to already contain the signal columns
    produced by ThaiTextPreprocessor.extract_signals_batch().
    Falls back to zeros if columns are missing (for inference on new data).
    """

    def __init__(self, feature_cols: list[str] | None = None):
        self.feature_cols = feature_cols or SIGNAL_FEATURE_COLS

    def fit(self, X, y=None):
        return self

    def transform(self, X) -> np.ndarray:
        if isinstance(X, pd.DataFrame):
            available = [c for c in self.feature_cols if c in X.columns]
            missing = [c for c in self.feature_cols if c not in X.columns]
            if missing:
                logger.warning(f"Missing signal columns (using 0): {missing}")
            result = np.zeros((len(X), len(self.feature_cols)), dtype=float)
            for i, col in enumerate(self.feature_cols):
                if col in X.columns:
                    result[:, i] = X[col].fillna(0).values
            return result
        # If X is a list/array of texts, extract signals on-the-fly
        from src.data.preprocessor import ThaiTextPreprocessor

        preprocessor = ThaiTextPreprocessor()
        signals = preprocessor.extract_signals_batch(X)
        return signals[self.feature_cols].fillna(0).values


class TextColumnSelector(BaseEstimator, TransformerMixin):
    """Select the text column from a DataFrame for TF-IDF input."""

    def __init__(self, column: str = "text_clean"):
        self.column = column

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            return X[self.column].fillna("").tolist()
        return X  # Assume it's already a list/array


def build_feature_pipeline(config: dict | None = None) -> Pipeline:
    """
    Build the complete feature extraction pipeline.

    Architecture:
        Input (DataFrame or list of texts)
            ├── TF-IDF Vectorizer (on text_clean)
            └── Signal Features (numerical columns)
        → Concatenated sparse + dense feature matrix

    Returns:
        sklearn Pipeline that outputs (n_samples, n_tfidf + n_signals) feature matrix
    """
    if config is None:
        cfg = get_config()
        tfidf_cfg = cfg["features"]["tfidf"]
    else:
        tfidf_cfg = config.get("tfidf", {})

    from sklearn.pipeline import FeatureUnion

    tfidf = TfidfVectorizer(
        max_features=tfidf_cfg.get("max_features", 5000),
        ngram_range=tuple(tfidf_cfg.get("ngram_range", [1, 2])),
        min_df=tfidf_cfg.get("min_df", 2),
        max_df=tfidf_cfg.get("max_df", 0.95),
        sublinear_tf=tfidf_cfg.get("sublinear_tf", True),
        analyzer="word",
        token_pattern=r"(?u)\b\w+\b",  # handles Thai characters
    )

    text_pipeline = Pipeline(
        [
            ("selector", TextColumnSelector("text_clean")),
            ("tfidf", tfidf),
        ]
    )

    signal_pipeline = Pipeline(
        [
            ("extractor", SignalFeatureExtractor()),
            ("scaler", StandardScaler()),
        ]
    )

    combined = FeatureUnion(
        [
            ("text_features", text_pipeline),
            ("signal_features", signal_pipeline),
        ]
    )

    logger.info(
        f"Feature pipeline built: TF-IDF(max_features={tfidf_cfg.get('max_features', 5000)}, "
        f"ngram={tfidf_cfg.get('ngram_range', [1, 2])}) + {len(SIGNAL_FEATURE_COLS)} signal features"
    )
    return combined


def get_tfidf_feature_names(pipeline) -> list[str]:
    """
    Extract feature names from a fitted FeatureUnion pipeline.

    Args:
        pipeline: Fitted pipeline with FeatureUnion containing 'text_features' and 'signal_features'

    Returns:
        List of feature name strings
    """
    try:
        fu = pipeline
        # Handle case where pipeline is wrapped in another Pipeline
        if hasattr(pipeline, "named_steps"):
            fu = pipeline.named_steps.get("features", pipeline)

        tfidf_names = (
            fu.transformer_list[0][1]
            .named_steps["tfidf"]
            .get_feature_names_out()
            .tolist()
        )
        signal_names = SIGNAL_FEATURE_COLS
        return tfidf_names + signal_names
    except Exception as e:
        logger.warning(f"Could not extract feature names: {e}")
        return []
