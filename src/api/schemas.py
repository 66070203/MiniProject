"""
Pydantic schemas for ScamGuard API request/response models.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PredictRequest(BaseModel):
    """Request body for the /predict endpoint."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The Thai text message to classify",
        examples=["ยินดีด้วยคุณได้รับรางวัล 50,000 บาท กดลิงก์เพื่อรับ"],
    )
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional user identifier for analytics",
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank or whitespace only")
        return v.strip()


class Probabilities(BaseModel):
    """Per-class prediction probabilities."""

    ham: float = Field(..., ge=0.0, le=1.0)
    spam: float = Field(..., ge=0.0, le=1.0)
    phishing: float = Field(..., ge=0.0, le=1.0)


class PredictResponse(BaseModel):
    """Response from the /predict endpoint."""

    label: str = Field(..., description="Predicted label: ham, spam, or phishing")
    label_th: str = Field(..., description="Thai label name")
    label_id: int = Field(..., description="Label integer (0=ham, 1=spam, 2=phishing)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    risk_level: str = Field(..., description="Risk level: low, medium, or high")
    risk_level_th: str = Field(..., description="Thai risk level description")
    explanation: str = Field(..., description="Human-readable Thai explanation")
    keywords: list[str] = Field(default_factory=list, description="Risk keywords found")
    probabilities: Probabilities
    processing_time_ms: float = Field(..., description="Inference time in milliseconds")
    confidence_source: str = Field(
        default="ml",
        description="Which stage made the final decision: 'ml' or 'hybrid' (ml+llm)",
    )
    llm_explanation: Optional[str] = Field(
        default=None,
        description="Thai-language reason from Groq LLM (only present in hybrid mode)",
    )


class FeedbackRequest(BaseModel):
    """Request body for the /feedback endpoint."""

    text: str = Field(..., min_length=1, max_length=2000)
    predicted_label: str = Field(..., description="What the model predicted")
    actual_label: str = Field(..., description="What the actual label should be")
    user_id: Optional[str] = Field(default=None, max_length=100)

    @field_validator("predicted_label", "actual_label")
    @classmethod
    def label_must_be_valid(cls, v: str) -> str:
        valid = {"ham", "spam", "phishing"}
        if v not in valid:
            raise ValueError(f"label must be one of {valid}")
        return v


class FeedbackResponse(BaseModel):
    """Response from the /feedback endpoint."""

    feedback_id: int
    message: str
    saved_at: str


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str
    model_loaded: bool
    model_version: str
    timestamp: str


class ModelInfoResponse(BaseModel):
    """Response from the /model-info endpoint."""

    model_name: str
    version: str
    trained_at: str
    val_accuracy: float
    train_samples: int
    label_names: list[str]


class StatsResponse(BaseModel):
    """Response from the /stats endpoint."""

    total_predictions: int
    spam_count: int
    phishing_count: int
    ham_count: int
    spam_rate: float
    phishing_rate: float
    feedback_count: int


# ---------------------------------------------------------------------------
# Chat schemas
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """ข้อความเดียวในประวัติการสนทนา"""

    role: str = Field(..., description="'user' หรือ 'assistant'")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="คำถามหรือข้อความจากผู้ใช้",
        examples=["ฟิชชิ่งคืออะไร", "ถ้าถูกหลอกให้โอนเงินแล้วควรทำอย่างไร"],
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="ประวัติการสนทนาก่อนหน้า (สูงสุด 10 รอบ)",
    )
    user_id: Optional[str] = Field(default=None, max_length=100)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v.strip()


class ChatResponse(BaseModel):
    """Response from the /chat endpoint."""

    reply: str = Field(..., description="คำตอบจาก AI")
    source: str = Field(
        default="llm",
        description="แหล่งที่มาของคำตอบ: 'llm', 'faq', หรือ 'fallback'",
    )
    timestamp: str = Field(..., description="เวลาที่ตอบ (ISO 8601 UTC)")
