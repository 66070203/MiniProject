"""
Inference / prediction module for GuardianShield.

Loads the trained model and provides prediction with explanation.
Supports Two-Stage Hybrid mode: ML Ensemble → Groq LLM (for low-confidence cases).
"""

import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from src.data.preprocessor import ThaiTextPreprocessor
from src.utils.config import get_config, get_project_root
from src.utils.logger import get_logger

logger = get_logger(__name__)

LABEL_NAMES = {0: "ham", 1: "spam", 2: "phishing"}
LABEL_NAMES_TH = {0: "ข้อความปกติ", 1: "สแปม", 2: "ฟิชชิ่ง (หลอกลวง)"}
RISK_LEVELS = {0: "low", 1: "high", 2: "high"}
RISK_LEVELS_TH = {0: "ต่ำ", 1: "สูง", 2: "สูงมาก"}

# Thai explanations for common signal patterns
SIGNAL_EXPLANATIONS_TH = {
    "url_count": "พบลิงก์ URL ในข้อความ",
    "phone_count": "พบหมายเลขโทรศัพท์ในข้อความ",
    "exclamation_count": "มีการใช้เครื่องหมายอัศเจรีย์มากผิดปกติ",
    "number_ratio": "มีตัวเลขจำนวนมากในข้อความ",
    "caps_ratio": "มีตัวพิมพ์ใหญ่จำนวนมาก",
}

# High-risk Thai keywords associated with spam/phishing
SPAM_KEYWORDS_TH = [
    "รางวัล",
    "ยินดีด้วย",
    "ฟรี",
    "ด่วน",
    "กด",
    "ลิงก์",
    "โปรโมชั่น",
    "ลดราคา",
    "เงินสด",
    "กู้เงิน",
    "ดอกเบี้ยต่ำ",
    "อนุมัติทันที",
]
PHISHING_KEYWORDS_TH = [
    "otp",
    "รหัส",
    "ยืนยัน",
    "บัญชี",
    "ธนาคาร",
    "บัตร",
    "ระงับ",
    "แจ้งเตือน",
    "ตำรวจ",
    "ศาล",
    "หมายเรียก",
    "กรมสรรพากร",
]


class GuardianPredictor:
    """
    Singleton predictor that loads the model once and handles inference.

    Supports Two-Stage Hybrid mode:
    - Stage 1: ML Voting Ensemble (always runs, fast)
    - Stage 2: Groq LLM (runs only when ML confidence < threshold)

    Usage:
        predictor = GuardianPredictor()
        result = predictor.predict("ยินดีด้วยคุณได้รับรางวัล กดลิงก์เพื่อรับ")
    """

    _instance = None

    def __new__(cls, model_path: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self, model_path: str | None = None) -> None:
        """Load model, preprocessor, and optionally Groq LLM. Safe to call multiple times."""
        if self._loaded:
            return

        cfg = get_config()
        root = get_project_root()

        if model_path is None:
            model_path = root / cfg["paths"]["models"] / "best_model.joblib"

        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Run 'python -m src.models.trainer' to train the model first."
            )

        logger.info(f"Loading model from: {model_path}")
        self.model = joblib.load(model_path)
        self.preprocessor = ThaiTextPreprocessor(
            remove_stopwords=cfg["preprocessing"]["remove_stopwords"],
            engine=cfg["preprocessing"]["thai_engine"],
        )

        # Load Groq LLM classifier (optional — degrades gracefully if key missing)
        try:
            llm_cfg: dict = cfg["llm"]
        except KeyError:
            llm_cfg = {}
        self._llm_threshold: float = float(llm_cfg.get("confidence_threshold", 0.80))
        self._llm_enabled: bool = bool(llm_cfg.get("enabled", True))
        self.groq_classifier = None
        if self._llm_enabled:
            from src.models.llm_classifier import get_groq_classifier

            llm_model = llm_cfg.get("model", "llama-3.3-70b-versatile")
            llm_timeout = int(llm_cfg.get("timeout_seconds", 10))
            self.groq_classifier = get_groq_classifier(
                model=llm_model,
                timeout=llm_timeout,
            )
            if self.groq_classifier:
                logger.info(
                    f"Groq LLM enabled (model={llm_model}, threshold={self._llm_threshold})"
                )

        self._loaded = True

        # Load metadata if available
        metadata_path = model_path.parent / "model_metadata.json"
        self.metadata = {}
        if metadata_path.exists():
            with open(metadata_path) as f:
                self.metadata = json.load(f)

        logger.info("Model loaded successfully.")

    def _explain(
        self, text: str, label: int, signals: dict, proba: np.ndarray
    ) -> tuple[str, list[str]]:
        """Generate a simple Thai-language explanation for the prediction."""
        keywords_found = []

        text_lower = text.lower()
        if label == 1:
            keywords_found = [kw for kw in SPAM_KEYWORDS_TH if kw.lower() in text_lower]
        elif label == 2:
            keywords_found = [
                kw for kw in PHISHING_KEYWORDS_TH if kw.lower() in text_lower
            ]

        signal_reasons = []
        if signals.get("url_count", 0) > 0:
            signal_reasons.append("พบลิงก์ URL")
        if signals.get("phone_count", 0) > 0:
            signal_reasons.append("พบเบอร์โทรศัพท์")
        if signals.get("exclamation_count", 0) > 2:
            signal_reasons.append("มีเครื่องหมายอัศเจรีย์มากผิดปกติ")

        if label == 0:
            explanation = "ข้อความนี้ดูเป็นปกติ ไม่พบสัญญาณอันตราย"
        elif label == 1:
            parts = []
            if keywords_found:
                parts.append(f"พบคำเสี่ยง: {', '.join(keywords_found[:5])}")
            parts.extend(signal_reasons)
            explanation = (
                " | ".join(parts) if parts else "รูปแบบข้อความคล้ายกับสแปมที่พบบ่อย"
            )
        else:
            parts = []
            if keywords_found:
                parts.append(f"พบคำที่ใช้หลอกลวง: {', '.join(keywords_found[:5])}")
            parts.extend(signal_reasons)
            explanation = (
                " | ".join(parts)
                if parts
                else "รูปแบบข้อความคล้ายกับการหลอกลวงทางออนไลน์"
            )

        all_keywords = list(
            set(keywords_found + [r.split(":")[0].strip() for r in signal_reasons])
        )
        return explanation, all_keywords[:8]

    def _label_str_to_id(self, label: str) -> int:
        reverse = {"ham": 0, "spam": 1, "phishing": 2}
        return reverse.get(label, 0)

    def predict(self, text: str, user_id: str | None = None) -> dict[str, Any]:
        """
        Predict whether a message is ham/spam/phishing.

        Two-stage hybrid:
        1. ML Ensemble always runs first.
        2. If confidence < threshold AND Groq is available → call LLM for second opinion.
           LLM label takes priority; confidence is averaged when labels agree.

        Args:
            text: Raw Thai text message
            user_id: Optional user identifier for logging

        Returns:
            Prediction result dict. Extra fields when LLM is used:
            - confidence_source: "ml" | "hybrid"
            - llm_explanation: Thai reason from LLM (or None)
        """
        if not self._loaded:
            self.load()

        if not text or not text.strip():
            return {
                "label": "ham",
                "label_th": LABEL_NAMES_TH[0],
                "label_id": 0,
                "confidence": 1.0,
                "risk_level": "low",
                "risk_level_th": RISK_LEVELS_TH[0],
                "explanation": "ข้อความว่างเปล่า",
                "keywords": [],
                "processing_time_ms": 0,
                "probabilities": {"ham": 1.0, "spam": 0.0, "phishing": 0.0},
                "confidence_source": "ml",
                "llm_explanation": None,
            }

        start = time.time()

        # ── Stage 1: ML Ensemble ──────────────────────────────────────────────
        signals = self.preprocessor.extract_signals(text)
        text_clean = self.preprocessor.process(text)

        import pandas as pd

        input_df = pd.DataFrame([{"text": text, "text_clean": text_clean, **signals}])

        proba = self.model.predict_proba(input_df)[0]
        ml_label_id = int(np.argmax(proba))
        ml_confidence = float(proba[ml_label_id])

        explanation, keywords = self._explain(text, ml_label_id, signals, proba)

        # ── Stage 2: Groq LLM (only when ML is uncertain) ────────────────────
        final_label_id = ml_label_id
        final_confidence = ml_confidence
        confidence_source = "ml"
        llm_explanation: str | None = None

        if self.groq_classifier is not None and ml_confidence < self._llm_threshold:
            logger.info(
                f"ML confidence={ml_confidence:.3f} < threshold={self._llm_threshold} "
                "→ calling Groq LLM"
            )
            try:
                llm_result = self.groq_classifier.classify(text)
                llm_label = llm_result["label"]
                llm_conf = llm_result["confidence"]
                llm_explanation = llm_result.get("reason")

                llm_label_id = self._label_str_to_id(llm_label)
                confidence_source = "hybrid"

                if llm_label_id == ml_label_id:
                    # Both agree → average confidence
                    final_confidence = round((ml_confidence + llm_conf) / 2, 4)
                    final_label_id = ml_label_id
                else:
                    # Disagree → LLM takes priority, use LLM confidence
                    logger.info(
                        f"ML={LABEL_NAMES[ml_label_id]} vs LLM={llm_label} → using LLM"
                    )
                    final_label_id = llm_label_id
                    final_confidence = round(llm_conf, 4)
                    # Re-generate explanation for the new label
                    explanation, keywords = self._explain(
                        text, final_label_id, signals, proba
                    )

                logger.info(
                    f"Hybrid result: label={LABEL_NAMES[final_label_id]} "
                    f"confidence={final_confidence:.3f} (ML={ml_confidence:.3f}, LLM={llm_conf:.3f})"
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Groq LLM call failed, falling back to ML: {exc}")
                confidence_source = "ml"

        elapsed_ms = (time.time() - start) * 1000

        return {
            "label": LABEL_NAMES[final_label_id],
            "label_th": LABEL_NAMES_TH[final_label_id],
            "label_id": final_label_id,
            "confidence": round(final_confidence, 4),
            "risk_level": RISK_LEVELS[final_label_id],
            "risk_level_th": RISK_LEVELS_TH[final_label_id],
            "explanation": explanation,
            "keywords": keywords,
            "processing_time_ms": round(elapsed_ms, 1),
            "probabilities": {
                "ham": round(float(proba[0]), 4),
                "spam": round(float(proba[1]), 4),
                "phishing": round(float(proba[2]), 4),
            },
            "confidence_source": confidence_source,
            "llm_explanation": llm_explanation,
        }

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (useful for testing with different models)."""
        cls._instance = None


def get_predictor(model_path: str | None = None) -> GuardianPredictor:
    """Get the global GuardianPredictor instance, loading if necessary."""
    predictor = GuardianPredictor(model_path)
    predictor.load(model_path)
    return predictor
