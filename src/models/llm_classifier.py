"""
Groq LLM classifier for ScamGuard.

Provides a second-opinion classification for low-confidence ML predictions
using the Groq API (llama-3.3-70b-versatile).
"""

import json
import os
import re
import time
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

VALID_LABELS = {"ham", "spam", "phishing"}

SYSTEM_PROMPT = """คุณเป็นผู้เชี่ยวชาญด้านความปลอดภัยไซเบอร์ที่เชี่ยวชาญข้อความภาษาไทย
หน้าที่ของคุณคือจำแนกข้อความ SMS/LINE เป็น 1 ในสามประเภท:
- "ham" = ข้อความปกติ ไม่เป็นอันตราย (เช่น ข้อความครอบครัว แจ้งข่าวจากธนาคารจริง นัดหมอ)
- "spam" = สแปม โฆษณา หรือข้อความชักชวนที่ไม่พึงประสงค์ (เช่น แจ้งรางวัล โปรโมชั่นหลอกลวง สินเชื่อด่วน)
- "phishing" = ฟิชชิ่ง หลอกลวงเพื่อขโมยข้อมูลส่วนตัว (เช่น ขอ OTP ขู่ระงับบัญชี แอบอ้างเป็นธนาคาร/ตำรวจ/กรมสรรพากร)

สัญญาณสำคัญของ phishing:
- มีการขอ OTP รหัสผ่าน หรือข้อมูลส่วนตัว
- ขู่ว่าบัญชีจะถูกระงับ/ปิด ถ้าไม่ดำเนินการ
- มีลิงก์ URL ที่ดูน่าสงสัยหรือไม่ใช่เว็บไซต์ทางการ
- แอบอ้างเป็นธนาคาร ตำรวจ ศาล หรือหน่วยงานราชการ

ตอบเฉพาะ JSON ในรูปแบบนี้เท่านั้น ห้ามมีข้อความอื่น:
{"label": "ham", "confidence": 0.95, "reason": "เหตุผลสั้นๆ เป็นภาษาไทย ไม่เกิน 2 ประโยค"}"""


class GroqClassifier:
    """
    Wrapper around Groq API for Thai spam/phishing classification.

    Usage:
        clf = GroqClassifier(api_key="gsk_...")
        result = clf.classify("ข้อความที่ต้องการจำแนก")
        # result: {"label": "ham", "confidence": 0.95, "reason": "..."}
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        timeout: int = 10,
    ) -> None:
        try:
            from groq import Groq  # type: ignore[import]

            self._client = Groq(api_key=api_key)
        except ImportError as exc:
            raise ImportError(
                "groq package is required. Run: pip install groq>=0.9.0"
            ) from exc

        self.model = model
        self.timeout = timeout
        logger.info(f"GroqClassifier initialized with model={model}")

    def classify(self, text: str) -> dict[str, Any]:
        """
        Classify Thai text using Groq LLM.

        Args:
            text: Raw Thai message text

        Returns:
            dict with keys: label (str), confidence (float), reason (str)

        Raises:
            ValueError: If LLM response cannot be parsed
            Exception: On API/network errors (caller should catch and fallback)
        """
        start = time.time()

        user_prompt = f'ข้อความ: "{text}"'

        chat = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )

        raw = chat.choices[0].message.content or ""
        elapsed_ms = (time.time() - start) * 1000
        logger.debug(f"Groq response ({elapsed_ms:.0f}ms): {raw!r}")

        result = self._parse_response(raw)
        return result

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Extract and validate JSON from LLM response."""
        # Find JSON object in response (handles cases with extra text)
        match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in LLM response: {raw!r}")

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON from LLM: {match.group()!r}") from exc

        label = str(data.get("label", "")).lower().strip()
        if label not in VALID_LABELS:
            raise ValueError(f"Invalid label from LLM: {label!r}")

        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        reason = str(data.get("reason", "")).strip()

        return {"label": label, "confidence": confidence, "reason": reason}


def get_groq_classifier(
    model: str = "llama-3.3-70b-versatile",
    timeout: int = 10,
) -> GroqClassifier | None:
    """
    Build a GroqClassifier from environment variable GROQ_API_KEY.
    Returns None if the key is not set (graceful degradation).
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        logger.info("GROQ_API_KEY not set — LLM stage disabled, ML-only mode.")
        return None
    try:
        return GroqClassifier(api_key=api_key, model=model, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to initialize GroqClassifier: {exc}")
        return None
