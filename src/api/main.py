"""
ScamGuard FastAPI backend application.

Endpoints:
    POST /predict       — Classify a Thai message as ham/spam/phishing
    POST /feedback      — Submit correction feedback
    GET  /health        — Health check
    GET  /model-info    — Model metadata
    GET  /stats         — Prediction statistics
    GET  /docs          — Auto-generated Swagger UI
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.chatbot import get_chatbot
from src.api.database import (
    get_session,
    get_stats,
    init_db,
    log_feedback,
    log_prediction,
)
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
    StatsResponse,
)
from src.models.predictor import get_predictor
from src.utils.config import get_config
from src.utils.logger import get_logger
from src.utils.mlflow_logger import log_prediction_to_mlflow

logger = get_logger(__name__)
cfg = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    logger.info("Starting ScamGuard API...")
    init_db()
    try:
        get_predictor()  # warm-up: load model at startup
        logger.info("Model loaded successfully.")
    except FileNotFoundError as e:
        logger.warning(f"Model not found at startup: {e}. Will retry on first request.")
    yield
    logger.info("Shutting down ScamGuard API.")


app = FastAPI(
    title=cfg["api"]["title"],
    description=cfg["api"]["description"],
    version=cfg["api"]["version"],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow Streamlit frontend and HuggingFace Spaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.time() - start) * 1000:.1f}ms"
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint. Returns service status and model availability."""
    try:
        predictor = get_predictor()
        model_loaded = predictor._loaded
        version = predictor.metadata.get("version", cfg["project"]["version"])
    except Exception:
        model_loaded = False
        version = cfg["project"]["version"]

    return HealthResponse(
        status="ok",
        model_loaded=model_loaded,
        model_version=version,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/model-info", response_model=ModelInfoResponse, tags=["System"])
async def model_info():
    """Return metadata about the currently loaded model."""
    try:
        predictor = get_predictor()
        meta = predictor.metadata
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Model not available: {e}")

    return ModelInfoResponse(
        model_name=meta.get("model_name", "VotingClassifier"),
        version=meta.get("version", cfg["project"]["version"]),
        trained_at=meta.get("trained_at", "unknown"),
        val_accuracy=meta.get("val_accuracy", 0.0),
        train_samples=meta.get("train_samples", 0),
        label_names=cfg["data"]["label_names"],
    )


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
async def predict(request: PredictRequest, db: Session = Depends(get_session)):
    """
    Classify a Thai text message as ham, spam, or phishing.

    Returns predicted label, confidence score, risk level, and explanation.
    """
    try:
        predictor = get_predictor()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Model not loaded. Please train the model first: {e}",
        )

    try:
        result = predictor.predict(request.text, user_id=request.user_id)
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    # Log prediction to database
    try:
        log_prediction(db, request.text, result, user_id=request.user_id)
    except Exception as e:
        logger.warning(f"Failed to log prediction to DB: {e}")

    # Log prediction to MLflow (non-blocking — failures are silently ignored)
    try:
        log_prediction_to_mlflow(request.text, result, user_id=request.user_id)
    except Exception as e:
        logger.warning(f"Failed to log prediction to MLflow: {e}")

    return PredictResponse(**result)


@app.post("/feedback", response_model=FeedbackResponse, tags=["Feedback"])
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_session)):
    """
    Submit correction feedback when the model prediction is wrong.

    Feedback is stored for future model retraining.
    """
    try:
        feedback = log_feedback(
            db,
            text=request.text,
            predicted=request.predicted_label,
            actual=request.actual_label,
            user_id=request.user_id,
        )
    except Exception as e:
        logger.error(f"Feedback logging error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Could not save feedback: {str(e)}"
        )

    return FeedbackResponse(
        feedback_id=feedback.id,
        message="ขอบคุณสำหรับข้อเสนอแนะ เราจะนำไปปรับปรุงระบบ",
        saved_at=datetime.utcnow().isoformat(),
    )


@app.get("/stats", response_model=StatsResponse, tags=["System"])
async def statistics(db: Session = Depends(get_session)):
    """Return aggregate prediction statistics."""
    try:
        stats = get_stats(db)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return StatsResponse(**stats)


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    ถามตอบเกี่ยวกับสแปม ฟิชชิ่ง วิธีรับมือ และวิธีแก้ไขเมื่อถูกหลอก

    รองรับการสนทนาต่อเนื่องผ่าน history field
    ใช้ Groq LLM เป็นหลัก พร้อม FAQ fallback เมื่อไม่มี API key
    """
    try:
        chatbot = get_chatbot()
        history = [msg.model_dump() for msg in request.history]
        result = chatbot.chat(message=request.message, history=history)
    except Exception as exc:
        logger.error(f"Chat error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(exc)}")

    return ChatResponse(**result)


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with project information."""
    return {
        "project": cfg["project"]["name"],
        "project_th": cfg["project"]["name_thai"],
        "version": cfg["project"]["version"],
        "description": cfg["project"]["description"],
        "docs": "/docs",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
    )
