"""
API endpoint tests using FastAPI TestClient.

Tests all endpoints with mocked model predictor so no trained model is required.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Mock predictor result used across tests
MOCK_PREDICT_RESULT = {
    "label": "spam",
    "label_th": "สแปม",
    "label_id": 1,
    "confidence": 0.92,
    "risk_level": "high",
    "risk_level_th": "สูง",
    "explanation": "พบคำเสี่ยง: รางวัล, กด, ลิงก์",
    "keywords": ["รางวัล", "กด"],
    "processing_time_ms": 15.2,
    "probabilities": {"ham": 0.05, "spam": 0.92, "phishing": 0.03},
}


@pytest.fixture(scope="module")
def client():
    """Create FastAPI TestClient with mocked predictor and DB."""
    from fastapi.testclient import TestClient

    from src.api import database
    from src.api.main import app

    # Initialize in-memory test DB
    database.init_db("sqlite:///:memory:")

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(autouse=True)
def mock_predictor():
    """Mock GuardianPredictor to avoid requiring a trained model."""
    mock = MagicMock()
    mock._loaded = True
    mock.metadata = {
        "model_name": "VotingClassifier",
        "version": "1.0.0",
        "trained_at": "2024-01-01T00:00:00",
        "val_accuracy": 0.94,
        "train_samples": 7000,
    }
    mock.predict.return_value = MOCK_PREDICT_RESULT

    with patch("src.api.main.get_predictor", return_value=mock):
        yield mock


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data
        assert "model_version" in data
        assert "timestamp" in data

    def test_health_status_ok(self, client):
        response = client.get("/health")
        assert response.json()["status"] == "ok"


class TestRootEndpoint:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_project_name(self, client):
        data = client.get("/").json()
        assert "project" in data
        assert data["project"] == "ScamGuard"


class TestModelInfoEndpoint:
    def test_model_info_returns_200(self, client):
        response = client.get("/model-info")
        assert response.status_code == 200

    def test_model_info_structure(self, client):
        data = client.get("/model-info").json()
        assert "model_name" in data
        assert "version" in data
        assert "val_accuracy" in data
        assert "label_names" in data

    def test_model_info_accuracy_valid(self, client):
        data = client.get("/model-info").json()
        assert 0.0 <= data["val_accuracy"] <= 1.0


class TestPredictEndpoint:
    def test_predict_valid_text(self, client):
        response = client.post("/predict", json={"text": "ยินดีด้วยคุณได้รับรางวัล"})
        assert response.status_code == 200

    def test_predict_response_structure(self, client):
        response = client.post("/predict", json={"text": "ยินดีด้วยคุณได้รับรางวัล"})
        data = response.json()
        required = [
            "label",
            "label_th",
            "confidence",
            "risk_level",
            "explanation",
            "probabilities",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_predict_label_is_valid(self, client):
        response = client.post("/predict", json={"text": "ทดสอบ"})
        data = response.json()
        assert data["label"] in ("ham", "spam", "phishing")

    def test_predict_confidence_range(self, client):
        response = client.post("/predict", json={"text": "ทดสอบ"})
        data = response.json()
        assert 0.0 <= data["confidence"] <= 1.0

    def test_predict_probabilities_sum_to_one(self, client):
        # Use actual mock values
        response = client.post("/predict", json={"text": "ทดสอบ"})
        data = response.json()
        proba = data["probabilities"]
        total = proba["ham"] + proba["spam"] + proba["phishing"]
        assert abs(total - 1.0) < 0.01

    def test_predict_empty_text_returns_422(self, client):
        response = client.post("/predict", json={"text": ""})
        assert response.status_code == 422

    def test_predict_whitespace_only_returns_422(self, client):
        response = client.post("/predict", json={"text": "   "})
        assert response.status_code == 422

    def test_predict_missing_text_field_returns_422(self, client):
        response = client.post("/predict", json={})
        assert response.status_code == 422

    def test_predict_with_user_id(self, client):
        response = client.post(
            "/predict",
            json={"text": "สวัสดี", "user_id": "test-user-001"},
        )
        assert response.status_code == 200

    def test_predict_text_too_long_returns_422(self, client):
        long_text = "ก" * 2001
        response = client.post("/predict", json={"text": long_text})
        assert response.status_code == 422


class TestFeedbackEndpoint:
    def test_feedback_valid_request(self, client):
        response = client.post(
            "/feedback",
            json={
                "text": "ยินดีด้วยคุณได้รับรางวัล",
                "predicted_label": "spam",
                "actual_label": "ham",
            },
        )
        assert response.status_code == 200

    def test_feedback_response_structure(self, client):
        response = client.post(
            "/feedback",
            json={
                "text": "ทดสอบ",
                "predicted_label": "ham",
                "actual_label": "ham",
            },
        )
        data = response.json()
        assert "feedback_id" in data
        assert "message" in data
        assert "saved_at" in data

    def test_feedback_invalid_label_returns_422(self, client):
        response = client.post(
            "/feedback",
            json={
                "text": "ทดสอบ",
                "predicted_label": "invalid_label",
                "actual_label": "ham",
            },
        )
        assert response.status_code == 422

    def test_feedback_missing_fields_returns_422(self, client):
        response = client.post("/feedback", json={"text": "ทดสอบ"})
        assert response.status_code == 422


class TestStatsEndpoint:
    def test_stats_returns_200(self, client):
        response = client.get("/stats")
        assert response.status_code == 200

    def test_stats_structure(self, client):
        response = client.get("/stats")
        data = response.json()
        required = [
            "total_predictions",
            "spam_count",
            "phishing_count",
            "ham_count",
            "spam_rate",
            "phishing_rate",
            "feedback_count",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_stats_counts_are_non_negative(self, client):
        data = client.get("/stats").json()
        assert data["total_predictions"] >= 0
        assert data["spam_count"] >= 0
        assert data["phishing_count"] >= 0
        assert data["ham_count"] >= 0
