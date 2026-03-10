"""
LINE Messaging API integration for ScamGuard.

Adds a POST /line/callback webhook endpoint that receives LINE messages,
classifies them with the ScamGuard predictor, and replies in Thai.

Required environment variables:
    LINE_CHANNEL_ACCESS_TOKEN   — from LINE Developers console
    LINE_CHANNEL_SECRET         — from LINE Developers console

These can be set in your .env file (same file as GROQ_API_KEY).
"""

import asyncio
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from src.models.predictor import get_predictor
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/line", tags=["LINE"])

# ---------------------------------------------------------------------------
# LINE SDK initialisation
# Initialised lazily so missing env vars produce a clear error on first
# request rather than crashing the entire app at import time.
# ---------------------------------------------------------------------------
_line_config: Configuration | None = None
_parser: WebhookParser | None = None


def _get_line_sdk() -> tuple[Configuration, WebhookParser]:
    global _line_config, _parser
    if _line_config is None or _parser is None:
        token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
        secret = os.environ.get("LINE_CHANNEL_SECRET", "").strip()
        if not token or not secret:
            raise RuntimeError(
                "LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET must be set. "
                "Add them to your .env file."
            )
        _line_config = Configuration(access_token=token)
        _parser = WebhookParser(secret)
    return _line_config, _parser


# ---------------------------------------------------------------------------
# Reply formatting  — persona: นุ้งสแปมการ์ด
# ---------------------------------------------------------------------------

def _format_reply(result: dict) -> str:
    """Convert a ScamGuard prediction dict into a conversational Thai LINE reply
    using the นุ้งสแปมการ์ด persona."""
    label = result.get("label", "")
    confidence_pct = round(result.get("confidence", 0) * 100)
    explanation = result.get("explanation", "")
    keywords = result.get("keywords", [])
    llm_explanation = result.get("llm_explanation")

    if label == "spam":
        lines = [
            f"อุ๊ย! ข้อความนี้เป็นสแปมเลยค่ะ ระวังด้วยนะ (มั่นใจ {confidence_pct}%)",
            "",
            explanation,
        ]
        if llm_explanation:
            lines += ["", llm_explanation]
        if keywords:
            lines += ["", f"คำที่น่าสงสัย: {', '.join(keywords)}"]
        lines += [
            "",
            "แนะนำอย่าตอบกลับหรือกดลิงก์อะไรนะคะ ลบทิ้งเลยดีกว่าค่ะ",
            "ถ้าสงสัยเพิ่มเติม โทร 1599 สายด่วนไซเบอร์ได้เลย ฟรี 24 ชม. ค่ะ",
        ]

    elif label == "phishing":
        lines = [
            f"โอ้โห อันตรายมากเลยค่ะ! ข้อความนี้คือฟิชชิ่ง พยายามหลอกขโมยข้อมูลชัดเจนเลย (มั่นใจ {confidence_pct}%)",
            "",
            explanation,
        ]
        if llm_explanation:
            lines += ["", llm_explanation]
        if keywords:
            lines += ["", f"สัญญาณอันตราย: {', '.join(keywords)}"]
        lines += [
            "",
            "ห้ามคลิกลิงก์ ห้ามให้ OTP หรือรหัสผ่านกับใครนะคะ อันตรายมากจริงๆ ค่ะ",
            "โทร 1599 สายด่วนไซเบอร์ด่วนเลยค่ะ ฟรี 24 ชม.",
        ]

    else:
        # fallback for unrecognised label
        risk_th = result.get("risk_level_th", result.get("risk_level", ""))
        lines = [
            f"ผลวิเคราะห์: {result.get('label_th', label)} | ความเสี่ยง: {risk_th} ({confidence_pct}%)",
            "",
            explanation,
        ]
        if llm_explanation:
            lines += ["", llm_explanation]
        if keywords:
            lines += ["", f"คำเตือน: {', '.join(keywords)}"]
        if label in ("spam", "phishing"):
            lines += ["", "โทร 1599 สายด่วนไซเบอร์ (ฟรี 24 ชม.)"]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------
@router.post("/callback")
async def line_callback(request: Request):
    """
    LINE Messaging API webhook.

    LINE sends a POST request here whenever a user sends a message to the bot.
    The signature in X-Line-Signature is validated before processing any events.
    """
    try:
        _, parser = _get_line_sdk()
    except RuntimeError as exc:
        logger.error("LINE SDK not configured: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))

    signature = request.headers.get("X-Line-Signature", "")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")

    body = await request.body()
    body_text = body.decode("utf-8")

    try:
        events = parser.parse(body_text, signature)
    except InvalidSignatureError:
        import base64, hashlib, hmac as _hmac
        secret = os.environ.get("LINE_CHANNEL_SECRET", "")
        computed = base64.b64encode(
            _hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
        ).decode("utf-8")
        logger.warning(
            "LINE webhook: invalid signature | received=%s | computed=%s | secret_len=%d | body_len=%d",
            signature, computed, len(secret), len(body),
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    # LINE sends an empty events list when verifying the webhook URL — return 200 OK
    await asyncio.gather(*[_handle_event(event) for event in events])

    return PlainTextResponse("OK")


# ---------------------------------------------------------------------------
# Event / message handlers
# ---------------------------------------------------------------------------
async def _handle_event(event) -> None:
    if isinstance(event, MessageEvent) and isinstance(
        event.message, TextMessageContent
    ):
        await _handle_text_message(event)
    # Non-text events (stickers, images, …) are silently ignored


async def _handle_text_message(event: MessageEvent) -> None:
    user_text = event.message.text
    reply_token = event.reply_token
    user_id = getattr(event.source, "user_id", None)

    logger.info(
        "LINE message received — user=%s len=%d", user_id or "unknown", len(user_text)
    )

    # --- classify with ScamGuard predictor ---
    reply_text: str | None = None
    try:
        predictor = get_predictor()
        result = predictor.predict(user_text, user_id=user_id)
        if result.get("label") in ("spam", "phishing"):
            reply_text = _format_reply(result)
        else:
            logger.info("LINE message classified as safe — no reply sent")
    except FileNotFoundError:
        logger.error("Model not loaded — cannot classify LINE message")
        reply_text = "ขออภัยนะคะ ตอนนี้ระบบยังไม่พร้อม ลองส่งมาใหม่อีกทีได้เลยค่ะ"
    except Exception as exc:
        logger.error("Prediction error for LINE message: %s", exc, exc_info=True)
        reply_text = "ขออภัยนะคะ เกิดข้อผิดพลาดในการวิเคราะห์ข้อความ ลองใหม่อีกครั้งได้เลยค่ะ"

    if reply_text is None:
        return

    # --- send reply ---
    try:
        line_config, _ = _get_line_sdk()
        with ApiClient(line_config) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )
    except Exception as exc:
        logger.error("Failed to send LINE reply: %s", exc, exc_info=True)
