"""
Tests for data pipeline: generator, preprocessor, validator.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


class TestSyntheticGenerator:
    """Tests for src/data/generator.py"""

    def test_generate_dataset_basic(self):
        from src.data.generator import generate_dataset

        df = generate_dataset(n_ham=10, n_spam=8, n_phishing=6, random_state=42)
        assert len(df) == 24
        assert "text" in df.columns
        assert "label" in df.columns
        assert "label_name" in df.columns
        assert "source" in df.columns

    def test_generate_dataset_label_distribution(self):
        from src.data.generator import generate_dataset

        df = generate_dataset(n_ham=50, n_spam=40, n_phishing=30, random_state=42)
        counts = df["label_name"].value_counts()
        assert counts["ham"] == 50
        assert counts["spam"] == 40
        assert counts["phishing"] == 30

    def test_generate_dataset_labels_are_valid(self):
        from src.data.generator import generate_dataset

        df = generate_dataset(n_ham=20, n_spam=15, n_phishing=10, random_state=0)
        assert set(df["label"].unique()).issubset({0, 1, 2})
        assert set(df["label_name"].unique()).issubset({"ham", "spam", "phishing"})

    def test_generate_dataset_no_empty_texts(self):
        from src.data.generator import generate_dataset

        df = generate_dataset(n_ham=20, n_spam=15, n_phishing=10, random_state=0)
        assert df["text"].notna().all()
        assert (df["text"].str.strip().str.len() > 0).all()

    def test_generate_dataset_reproducible(self):
        from src.data.generator import generate_dataset

        df1 = generate_dataset(n_ham=10, n_spam=8, n_phishing=6, random_state=42)
        df2 = generate_dataset(n_ham=10, n_spam=8, n_phishing=6, random_state=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_generate_dataset_save(self, tmp_path):
        from src.data.generator import generate_dataset

        df = generate_dataset(n_ham=5, n_spam=4, n_phishing=3, random_state=0)
        output = tmp_path / "test_synthetic.csv"
        df.to_csv(output, index=False)
        loaded = pd.read_csv(output)
        assert len(loaded) == 12


class TestThaiTextPreprocessor:
    """Tests for src/data/preprocessor.py"""

    def test_init(self, preprocessor):
        assert preprocessor is not None

    def test_clean_removes_urls(self, preprocessor):
        text = "กด https://bit.ly/fake เพื่อรับรางวัล"
        cleaned = preprocessor.clean(text)
        assert "https://" not in cleaned
        assert "bit.ly" not in cleaned

    def test_clean_replaces_phone(self, preprocessor):
        text = "โทร 062-345-6789 ทันที"
        cleaned = preprocessor.clean(text)
        assert "062-345-6789" not in cleaned

    def test_clean_handles_empty_string(self, preprocessor):
        assert preprocessor.clean("") == ""

    def test_clean_handles_none_gracefully(self, preprocessor):
        assert preprocessor.clean(None) == ""

    def test_process_returns_string(self, preprocessor):
        result = preprocessor.process("สวัสดีครับ")
        assert isinstance(result, str)

    def test_process_batch_length(self, preprocessor):
        texts = ["ข้อความหนึ่ง", "ข้อความสอง", "ข้อความสาม"]
        results = preprocessor.process_batch(texts)
        assert len(results) == 3

    def test_extract_signals_url_count(self, preprocessor):
        text = "กด https://example.com และ http://other.net เพื่อรับรางวัล"
        signals = preprocessor.extract_signals(text)
        assert signals["url_count"] >= 1

    def test_extract_signals_phone_count(self, preprocessor):
        text = "โทร 062-345-6789 หรือ 081-234-5678 ด่วน"
        signals = preprocessor.extract_signals(text)
        assert signals["phone_count"] >= 1

    def test_extract_signals_exclamation(self, preprocessor):
        text = "ยินดีด้วย! คุณได้รับรางวัล! ด่วน!"
        signals = preprocessor.extract_signals(text)
        assert signals["exclamation_count"] == 3

    def test_extract_signals_text_length(self, preprocessor):
        text = "สวัสดี"
        signals = preprocessor.extract_signals(text)
        assert signals["text_length"] == len(text)

    def test_extract_signals_batch_returns_dataframe(self, preprocessor):
        import pandas as pd

        texts = ["สวัสดี", "ยินดีด้วย! รับรางวัล: http://link.com"]
        df = preprocessor.extract_signals_batch(texts)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "url_count" in df.columns


class TestDataValidator:
    """Tests for src/data/validator.py"""

    def test_validate_raw_passes_valid_data(self, sample_df):
        from src.data.validator import validate_raw

        report = validate_raw(sample_df)
        assert report.n_rows == 6
        # Labels check
        assert set(report.label_distribution.keys()).issubset({0, 1, 2})

    def test_validate_raw_catches_missing_text(self):
        from src.data.validator import validate_raw

        df = pd.DataFrame(
            [
                {
                    "message_id": "x",
                    "text": None,
                    "label": 0,
                    "label_name": "ham",
                    "source": "test",
                    "created_at": "2024-01-01",
                }
            ]
        )
        report = validate_raw(df)
        assert not report.passed or len(report.issues) > 0

    def test_validate_raw_catches_invalid_label(self):
        from src.data.validator import validate_raw

        df = pd.DataFrame(
            [
                {
                    "message_id": "x",
                    "text": "สวัสดี",
                    "label": 99,  # invalid
                    "label_name": "unknown",
                    "source": "test",
                    "created_at": "2024-01-01",
                }
            ]
        )
        report = validate_raw(df)
        assert not report.passed

    def test_save_schema(self, tmp_path):
        from src.data.validator import save_schema

        output = tmp_path / "schema.json"
        path = save_schema(str(output))
        assert Path(path).exists()
        import json

        with open(path) as f:
            schema = json.load(f)
        assert "columns" in schema
        assert "label" in schema["columns"]

    def test_validate_label_distribution_in_report(self, sample_df):
        from src.data.validator import validate_raw

        report = validate_raw(sample_df)
        assert 0 in report.label_distribution
        assert 1 in report.label_distribution
        assert 2 in report.label_distribution


class TestPreprocessDataFrame:
    """Tests for preprocess_dataframe function."""

    def test_adds_text_clean_column(self, sample_df, preprocessor):
        from src.data.preprocessor import preprocess_dataframe

        result = preprocess_dataframe(sample_df, preprocessor=preprocessor)
        assert "text_clean" in result.columns

    def test_adds_signal_columns(self, sample_df, preprocessor):
        from src.data.preprocessor import preprocess_dataframe

        result = preprocess_dataframe(sample_df, preprocessor=preprocessor)
        assert "url_count" in result.columns
        assert "phone_count" in result.columns
        assert "text_length" in result.columns

    def test_preserves_label_column(self, sample_df, preprocessor):
        from src.data.preprocessor import preprocess_dataframe

        result = preprocess_dataframe(sample_df, preprocessor=preprocessor)
        assert "label" in result.columns
        assert list(result["label"]) == list(sample_df["label"])

    def test_no_empty_cleaned_texts(self, sample_df, preprocessor):
        from src.data.preprocessor import preprocess_dataframe

        result = preprocess_dataframe(sample_df, preprocessor=preprocessor)
        assert (result["text_clean"].str.strip().str.len() > 0).all()


class TestIngestionUtils:
    """Tests for ingestion helper functions."""

    def test_translate_approximate_replaces_keywords(self):
        from src.data.ingestion import _translate_approximate

        result = _translate_approximate("you are the winner, get free cash now!")
        # At least one English spam keyword should be replaced with Thai
        assert any(th in result for th in ["ผู้ชนะ", "ฟรี", "เงินสด", "ด่วน"])

    def test_translate_approximate_is_idempotent_for_thai(self):
        from src.data.ingestion import _translate_approximate

        thai_text = "สวัสดีครับ"
        assert _translate_approximate(thai_text) == thai_text


class TestConfigUtils:
    """Tests for config utility methods."""

    def test_config_get_nested_key(self):
        from src.utils.config import get_config

        cfg = get_config()
        name = cfg.get("project", "name")
        assert name == "ScamGuard"

    def test_config_get_missing_key_returns_default(self):
        from src.utils.config import get_config

        cfg = get_config()
        val = cfg.get("nonexistent_key", default="fallback")
        assert val == "fallback"

    def test_config_get_traverses_non_dict_returns_default(self):
        from src.utils.config import get_config

        cfg = get_config()
        # "project" → "name" → "subelement": at the third key, val is a string not dict
        val = cfg.get("project", "name", "deeper")
        assert val is None

    def test_config_reset_and_reinit(self):
        from src.utils.config import Config, get_config

        Config.reset()
        cfg = get_config()
        assert cfg["project"]["name"] == "ScamGuard"
