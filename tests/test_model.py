"""
Tests for ML model components: feature engineering, trainer, evaluator, predictor.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestFeatureEngineering:
    """Tests for src/features/feature_engineering.py"""

    def test_build_feature_pipeline_returns_pipeline(self):
        from src.features.feature_engineering import build_feature_pipeline

        pipeline = build_feature_pipeline()
        assert pipeline is not None

    def test_signal_extractor_with_dataframe(self, sample_df, preprocessor):
        from src.data.preprocessor import preprocess_dataframe
        from src.features.feature_engineering import SignalFeatureExtractor

        processed = preprocess_dataframe(sample_df, preprocessor=preprocessor)
        extractor = SignalFeatureExtractor()
        result = extractor.fit_transform(processed)
        assert result.shape[0] == len(processed)
        assert result.shape[1] == 7  # 7 signal features

    def test_signal_extractor_handles_missing_columns(self, sample_df):
        from src.features.feature_engineering import SignalFeatureExtractor

        # DataFrame without signal columns
        extractor = SignalFeatureExtractor()
        result = extractor.fit_transform(sample_df)
        assert result.shape[0] == len(sample_df)

    def test_text_column_selector_with_dataframe(self, sample_df, preprocessor):
        from src.data.preprocessor import preprocess_dataframe
        from src.features.feature_engineering import TextColumnSelector

        processed = preprocess_dataframe(sample_df, preprocessor=preprocessor)
        selector = TextColumnSelector("text_clean")
        result = selector.fit_transform(processed)
        assert isinstance(result, list)
        assert len(result) == len(processed)
        assert all(isinstance(t, str) for t in result)

    def test_feature_pipeline_fit_transform(self, sample_df, preprocessor):
        from src.data.preprocessor import preprocess_dataframe
        from src.features.feature_engineering import build_feature_pipeline

        processed = preprocess_dataframe(sample_df, preprocessor=preprocessor)
        pipeline = build_feature_pipeline()
        features = pipeline.fit_transform(processed)
        # Should produce (n_samples, n_tfidf + n_signals) matrix
        assert features.shape[0] == len(processed)
        assert features.shape[1] > 7  # at least signal features + some TF-IDF

    def test_build_feature_pipeline_with_explicit_config(self):
        from src.features.feature_engineering import build_feature_pipeline

        config = {
            "tfidf": {
                "max_features": 50,
                "ngram_range": [1, 1],
                "min_df": 1,
                "max_df": 1.0,
                "sublinear_tf": False,
            }
        }
        pipeline = build_feature_pipeline(config=config)
        assert pipeline is not None

    def test_signal_extractor_with_list_input(self):
        from src.features.feature_engineering import SignalFeatureExtractor

        texts = ["สวัสดีครับ", "ยินดีด้วย ได้รับรางวัล กดลิงก์"]
        extractor = SignalFeatureExtractor()
        result = extractor.fit_transform(texts)
        assert result.shape[0] == 2
        assert result.shape[1] == 7

    def test_text_selector_with_list_input(self):
        from src.features.feature_engineering import TextColumnSelector

        texts = ["สวัสดี", "ยินดีด้วย"]
        selector = TextColumnSelector()
        result = selector.transform(texts)
        assert result == texts


class TestEvaluator:
    """Tests for src/models/evaluator.py"""

    def test_compute_metrics_perfect_prediction(self):
        from src.models.evaluator import compute_metrics

        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 1, 2])
        metrics = compute_metrics(y_true, y_pred)
        assert metrics["accuracy"] == pytest.approx(1.0)
        assert metrics["f1_weighted"] == pytest.approx(1.0)

    def test_compute_metrics_with_probabilities(self):
        from src.models.evaluator import compute_metrics

        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 1, 1])
        y_proba = np.array(
            [
                [0.9, 0.05, 0.05],
                [0.1, 0.8, 0.1],
                [0.1, 0.1, 0.8],
                [0.85, 0.1, 0.05],
                [0.1, 0.75, 0.15],
                [0.1, 0.6, 0.3],  # wrong prediction
            ]
        )
        metrics = compute_metrics(y_true, y_pred, y_proba)
        assert "auc_roc_weighted" in metrics
        assert 0.0 <= metrics["auc_roc_weighted"] <= 1.0

    def test_compute_metrics_returns_required_keys(self):
        from src.models.evaluator import compute_metrics

        y_true = np.array([0, 1, 2])
        y_pred = np.array([0, 1, 2])
        metrics = compute_metrics(y_true, y_pred)
        required = [
            "accuracy",
            "f1_weighted",
            "precision_weighted",
            "recall_weighted",
            "f1_macro",
        ]
        for key in required:
            assert key in metrics, f"Missing metric: {key}"

    def test_get_classification_report(self):
        from src.models.evaluator import get_classification_report

        y_true = np.array([0, 1, 2, 0])
        y_pred = np.array([0, 1, 2, 1])
        report = get_classification_report(y_true, y_pred)
        assert isinstance(report, str)
        assert "ham" in report or "spam" in report

    def test_get_confusion_matrix_shape(self):
        from src.models.evaluator import get_confusion_matrix

        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 1, 2])
        cm = get_confusion_matrix(y_true, y_pred)
        assert cm.shape == (3, 3)


class TestPredictorUnit:
    """Unit tests for predictor logic (without loaded model)."""

    def test_predictor_is_singleton(self):
        from src.models.predictor import GuardianPredictor

        GuardianPredictor.reset()
        p1 = GuardianPredictor()
        p2 = GuardianPredictor()
        assert p1 is p2

    def test_predictor_raises_without_model(self, tmp_path):
        from src.models.predictor import GuardianPredictor

        GuardianPredictor.reset()
        predictor = GuardianPredictor()
        with pytest.raises(FileNotFoundError):
            predictor.load(model_path=str(tmp_path / "nonexistent.joblib"))

    def test_label_names_coverage(self):
        from src.models.predictor import LABEL_NAMES, LABEL_NAMES_TH, RISK_LEVELS

        for i in range(3):
            assert i in LABEL_NAMES
            assert i in LABEL_NAMES_TH
            assert i in RISK_LEVELS


class TestEndToEndTraining:
    """Integration test: full training pipeline on tiny dataset."""

    @pytest.fixture(scope="class")
    def trained_model_and_df(self, tmp_path_factory):
        """Train a minimal model on synthetic data for testing."""
        tmp = tmp_path_factory.mktemp("model_test")

        import joblib
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline

        from src.data.generator import generate_dataset
        from src.data.preprocessor import ThaiTextPreprocessor, preprocess_dataframe
        from src.features.feature_engineering import build_feature_pipeline

        # Generate small dataset
        df = generate_dataset(n_ham=100, n_spam=80, n_phishing=60, random_state=42)
        preprocessor = ThaiTextPreprocessor(remove_stopwords=False)
        df = preprocess_dataframe(df, preprocessor=preprocessor)

        train_df, val_df = train_test_split(
            df, test_size=0.2, stratify=df["label"], random_state=42
        )

        # Build minimal pipeline
        feature_pipe = build_feature_pipeline()
        clf = LogisticRegression(C=1.0, max_iter=200, random_state=42)
        pipeline = Pipeline([("features", feature_pipe), ("classifier", clf)])
        pipeline.fit(train_df, train_df["label"])

        model_path = tmp / "test_model.joblib"
        joblib.dump(pipeline, model_path)

        return pipeline, val_df, model_path

    def test_model_predict_shape(self, trained_model_and_df):
        pipeline, val_df, _ = trained_model_and_df
        preds = pipeline.predict(val_df)
        assert len(preds) == len(val_df)
        assert set(preds).issubset({0, 1, 2})

    def test_model_predict_proba_shape(self, trained_model_and_df):
        pipeline, val_df, _ = trained_model_and_df
        proba = pipeline.predict_proba(val_df)
        assert proba.shape == (len(val_df), 3)
        assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-5)

    def test_model_accuracy_above_threshold(self, trained_model_and_df):
        from src.models.evaluator import compute_metrics

        pipeline, val_df, _ = trained_model_and_df
        y_pred = pipeline.predict(val_df)
        y_proba = pipeline.predict_proba(val_df)
        metrics = compute_metrics(val_df["label"].values, y_pred, y_proba)
        # Minimum bar for a working model on synthetic data
        assert (
            metrics["accuracy"] >= 0.70
        ), f"Model accuracy {metrics['accuracy']:.3f} is below 70% threshold"

    def test_predictor_with_trained_model(self, trained_model_and_df):
        """Test GuardianPredictor with a locally trained model."""
        from src.models.predictor import GuardianPredictor

        pipeline, _, model_path = trained_model_and_df

        GuardianPredictor.reset()
        predictor = GuardianPredictor()
        predictor.load(str(model_path))
        predictor.model = pipeline  # inject test model

        result = predictor.predict("ยินดีด้วยคุณได้รับรางวัล 100,000 บาท")
        assert "label" in result
        assert "confidence" in result
        assert result["label"] in ("ham", "spam", "phishing")
        assert 0.0 <= result["confidence"] <= 1.0
        assert "explanation" in result
        assert "keywords" in result
        assert "probabilities" in result

    def test_predictor_empty_text(self, trained_model_and_df):
        from src.models.predictor import GuardianPredictor

        pipeline, _, model_path = trained_model_and_df

        GuardianPredictor.reset()
        predictor = GuardianPredictor()
        predictor.load(str(model_path))
        predictor.model = pipeline

        result = predictor.predict("")
        assert result["label"] == "ham"
        assert result["confidence"] == 1.0

    def test_get_predictor_and_double_load(self, trained_model_and_df):
        from src.models.predictor import GuardianPredictor, get_predictor

        _, _, model_path = trained_model_and_df

        GuardianPredictor.reset()
        predictor = get_predictor(str(model_path))
        assert predictor is not None
        # Second call exercises the early-return branch when already loaded
        predictor.load(str(model_path))

    def test_evaluate_on_test_set(self, trained_model_and_df, tmp_path):
        from src.models.evaluator import evaluate_on_test_set

        pipeline, val_df, _ = trained_model_and_df

        test_csv = tmp_path / "test.csv"
        val_df.to_csv(test_csv, index=False)
        output_path = tmp_path / "report.json"

        result = evaluate_on_test_set(
            pipeline, test_path=str(test_csv), output_path=str(output_path)
        )
        assert "metrics" in result
        assert "accuracy" in result["metrics"]
        assert output_path.exists()

    def test_get_tfidf_feature_names(self, trained_model_and_df):
        from src.features.feature_engineering import get_tfidf_feature_names

        pipeline, _, _ = trained_model_and_df
        feature_pipe = pipeline.named_steps["features"]
        names = get_tfidf_feature_names(feature_pipe)
        assert isinstance(names, list)
        assert len(names) > 0
