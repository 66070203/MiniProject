"""
Chatbot service สำหรับ ScamGuard
ตอบคำถามเกี่ยวกับสแปม ฟิชชิ่ง วิธีรับมือ และวิธีแก้ไขเมื่อถูกหลอก
ใช้ Groq LLM (llama-3.3-70b-versatile) เป็นหลัก พร้อม FAQ fallback
"""

import os
from datetime import datetime
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

CHATBOT_SYSTEM_PROMPT = """คุณเป็นผู้ช่วยด้านความปลอดภัยไซเบอร์ชื่อ "น้องการ์ด" จากระบบ ScamGuard
ออกแบบมาเพื่อช่วยผู้สูงอายุและประชาชนทั่วไปให้เข้าใจและป้องกันตนเองจากสแปม ฟิชชิ่ง และการหลอกลวงออนไลน์

หน้าที่ของคุณ:
1. ตอบคำถามเกี่ยวกับสแปม ฟิชชิ่ง และการหลอกลวงออนไลน์รูปแบบต่างๆ
2. อธิบายวิธีสังเกตข้อความอันตราย
3. แนะนำขั้นตอนที่ทำได้ทันทีเมื่อได้รับข้อความน่าสงสัย
4. แนะนำขั้นตอนการแก้ไขเมื่อถูกหลอกลวง (เช่น อายัดบัญชี แจ้งความ ติดต่อธนาคาร)
5. ให้ความรู้เบื้องต้นด้านความปลอดภัยไซเบอร์ที่เข้าใจง่าย

กฎการตอบ:
- ใช้ภาษาไทยที่เรียบง่าย เข้าใจง่าย เหมาะกับผู้สูงอายุ หลีกเลี่ยงศัพท์เทคนิค
- ตอบสั้น กระชับ ชัดเจน แบ่งเป็นข้อๆ เพื่ออ่านง่าย
- ถ้าถามเรื่องอื่นนอกเหนือจากความปลอดภัยไซเบอร์/การหลอกลวง ให้บอกสั้นๆ ว่าไม่ใช่หัวข้อที่เชี่ยวชาญ แล้วถามกลับว่ามีคำถามด้านความปลอดภัยไหม
- เน้นหมายเลขฉุกเฉินเสมอเมื่อเหมาะสม:
  • สายด่วนไซเบอร์: 1599 (24 ชั่วโมง ฟรี)
  • สายด่วนธนาคารแห่งประเทศไทย: 1213
  • สายด่วนตำรวจ: 191
  • DSI (กรมสอบสวนคดีพิเศษ): 1202
- ถ้าผู้ใช้บอกว่าเพิ่งถูกหลอก ให้ตอบอย่างเห็นอกเห็นใจและให้ขั้นตอนที่ทำได้ทันทีก่อน"""

# คำถามที่พบบ่อย — ใช้เป็น fallback เมื่อ Groq ไม่พร้อม
FAQ: dict[str, str] = {
    "สแปมคืออะไร": (
        "**สแปม** คือข้อความที่ถูกส่งมาโดยไม่ได้ขออนุญาต มักเป็นโฆษณา หรือชักชวนสิ่งที่ไม่ต้องการ\n\n"
        "**ตัวอย่าง:**\n"
        "• ข้อความโปรโมชั่น ลด 50%\n"
        "• แจ้งว่าได้รับรางวัลที่ไม่ได้สมัคร\n"
        "• ชักชวนสมัครสินเชื่อ/ประกัน\n\n"
        "**วิธีรับมือ:** ไม่ต้องตอบ ลบทิ้ง หรือบล็อกเบอร์นั้น"
    ),
    "ฟิชชิ่งคืออะไร": (
        "**ฟิชชิ่ง** คือการหลอกลวงเพื่อขโมยข้อมูลส่วนตัว เช่น รหัสบัตร รหัส OTP หรือรหัสผ่าน\n\n"
        "**สัญญาณเตือน:**\n"
        "• แอบอ้างเป็นธนาคาร ตำรวจ หรือหน่วยงานราชการ\n"
        "• ขู่ว่าบัญชีจะถูกระงับถ้าไม่ดำเนินการด่วน\n"
        "• ขอ OTP รหัสผ่าน หรือข้อมูลส่วนตัว\n"
        "• มีลิงก์ URL ที่ดูแปลกหรือสั้น เช่น bit.ly/...\n\n"
        "**วิธีรับมือ:** อย่ากดลิงก์ อย่าให้ข้อมูลใดๆ โทร 1599 ถ้าสงสัย"
    ),
    "ถูกหลอกแล้วทำอย่างไร": (
        "ถ้าเพิ่งถูกหลอก ให้ทำทันทีตามขั้นตอนนี้:\n\n"
        "**1. อายัดบัญชีก่อนเลย**\n"
        "• โทรหาธนาคารที่หลังบัตร หรือผ่านแอปธนาคาร\n"
        "• ขอระงับบัตร/บัญชีชั่วคราว\n\n"
        "**2. แจ้งความ**\n"
        "• โทร 1599 (สายด่วนไซเบอร์) ได้ทันที ฟรี 24 ชม.\n"
        "• หรือไปแจ้งที่สถานีตำรวจใกล้บ้าน\n\n"
        "**3. เก็บหลักฐาน**\n"
        "• ถ่ายรูปหน้าจอข้อความ/บทสนทนา\n"
        "• จดเบอร์โทร บัญชีที่โอนเงิน ลิงก์ที่กด\n\n"
        "**4. เปลี่ยนรหัสผ่าน**\n"
        "• เปลี่ยนรหัสแอปธนาคาร อีเมล LINE ทั้งหมด"
    ),
    "วิธีสังเกตข้อความอันตราย": (
        "**สัญญาณอันตราย ให้ระวัง:**\n\n"
        "🚨 **อันตรายมาก:**\n"
        "• ขอ OTP รหัสผ่าน หรือเลขบัตร\n"
        "• ขู่ว่าบัญชีจะถูกปิด/อายัด\n"
        "• แอบอ้างเป็นธนาคาร ตำรวจ ศาล หรือราชการ\n\n"
        "⚠️ **น่าสงสัย:**\n"
        "• มีรางวัลหรือเงินที่ไม่ได้สมัคร\n"
        "• มีลิงก์แปลกๆ หรือ URL สั้น\n"
        "• เร่งรัดให้ทำอะไรภายในเวลาจำกัด\n"
        "• มีเบอร์โทรที่ไม่รู้จัก\n\n"
        "✅ **ถ้าสงสัย:** อย่าตอบ อย่ากด โทรถามคนที่ไว้ใจหรือโทร 1599"
    ),
    "otp คืออะไร": (
        "**OTP** (One-Time Password) คือรหัสที่ใช้ได้ครั้งเดียว มักส่งผ่าน SMS\n\n"
        "**ข้อควรจำ:**\n"
        "• ธนาคารจะ **ไม่มีวัน** โทรขอ OTP จากคุณ\n"
        "• OTP ที่แท้จริงคุณต้องขอมาเอง ไม่ใช่ระบบส่งมาให้แล้วขอ\n"
        "• ถ้าใครขอ OTP → **เป็นมิจฉาชีพ 100%**\n\n"
        "**สิ่งที่ต้องทำ:** วางสายทันที อย่าบอก OTP กับใครเลย"
    ),
    "สายด่วน": (
        "**หมายเลขสายด่วนที่ควรจำ:**\n\n"
        "📞 **1599** — สายด่วนไซเบอร์ (DSI) ฟรี 24 ชั่วโมง\n"
        "📞 **1213** — ธนาคารแห่งประเทศไทย\n"
        "📞 **191** — ตำรวจ (เหตุฉุกเฉิน)\n"
        "📞 **1202** — DSI กรมสอบสวนคดีพิเศษ\n\n"
        "**แนะนำ:** บันทึกเบอร์ 1599 ไว้ในโทรศัพท์เดี๋ยวนี้เลยครับ/ค่ะ"
    ),
}


def _find_faq_answer(question: str) -> str | None:
    """ค้นหาคำตอบ FAQ แบบ keyword matching"""
    question_lower = question.lower()
    keyword_map = {
        "สแปม": "สแปมคืออะไร",
        "spam": "สแปมคืออะไร",
        "ฟิชชิ่ง": "ฟิชชิ่งคืออะไร",
        "phishing": "ฟิชชิ่งคืออะไร",
        "ถูกหลอก": "ถูกหลอกแล้วทำอย่างไร",
        "โดนโกง": "ถูกหลอกแล้วทำอย่างไร",
        "โอนเงิน": "ถูกหลอกแล้วทำอย่างไร",
        "สังเกต": "วิธีสังเกตข้อความอันตราย",
        "อันตราย": "วิธีสังเกตข้อความอันตราย",
        "รู้ได้อย่างไร": "วิธีสังเกตข้อความอันตราย",
        "otp": "otp คืออะไร",
        "รหัส": "otp คืออะไร",
        "สายด่วน": "สายด่วน",
        "โทร": "สายด่วน",
        "1599": "สายด่วน",
        "แจ้งความ": "ถูกหลอกแล้วทำอย่างไร",
    }
    for kw, faq_key in keyword_map.items():
        if kw in question_lower:
            return FAQ[faq_key]
    return None


def build_groq_messages(
    history: list[dict[str, str]],
    new_message: str,
) -> list[dict[str, str]]:
    """สร้าง message list สำหรับ Groq API"""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": CHATBOT_SYSTEM_PROMPT}
    ]
    for msg in history[-10:]:  # จำกัด 10 รอบล่าสุด
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": new_message})
    return messages


class ScamGuardChatbot:
    """
    Chatbot สำหรับตอบคำถามด้านความปลอดภัยไซเบอร์
    ใช้ Groq LLM ถ้ามี API key มิเช่นนั้นใช้ FAQ fallback
    """

    def __init__(self) -> None:
        self._groq_client = None
        self._model = "llama-3.3-70b-versatile"
        self._init_groq()

    def _init_groq(self) -> None:
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            logger.info("GROQ_API_KEY ไม่ได้ตั้งค่า — chatbot ใช้ FAQ fallback")
            return
        try:
            from groq import Groq  # type: ignore[import]

            self._groq_client = Groq(api_key=api_key)
            logger.info("ScamGuardChatbot: เชื่อมต่อ Groq สำเร็จ")
        except ImportError:
            logger.warning("ไม่พบ groq package — chatbot ใช้ FAQ fallback")
        except Exception as exc:
            logger.warning(f"ไม่สามารถเชื่อมต่อ Groq: {exc}")

    @property
    def has_llm(self) -> bool:
        return self._groq_client is not None

    def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        ตอบคำถามผู้ใช้

        Args:
            message: ข้อความจากผู้ใช้
            history: ประวัติการสนทนา [{"role": "user"/"assistant", "content": "..."}]

        Returns:
            {"reply": str, "source": "llm" | "faq", "timestamp": str}
        """
        history = history or []
        timestamp = datetime.utcnow().isoformat()

        if self._groq_client is not None:
            try:
                reply = self._call_groq(message, history)
                return {"reply": reply, "source": "llm", "timestamp": timestamp}
            except Exception as exc:
                logger.warning(f"Groq error — ใช้ FAQ fallback: {exc}")

        # FAQ fallback
        faq_answer = _find_faq_answer(message)
        if faq_answer:
            return {"reply": faq_answer, "source": "faq", "timestamp": timestamp}

        return {
            "reply": (
                "ขออภัยครับ/ค่ะ ไม่สามารถเชื่อมต่อระบบ AI ได้ในขณะนี้\n\n"
                "สำหรับความช่วยเหลือด่วน:\n"
                "📞 **สายด่วนไซเบอร์ 1599** (ฟรี 24 ชั่วโมง)\n\n"
                "หรือลองถามใหม่อีกครั้งในภายหลัง"
            ),
            "source": "fallback",
            "timestamp": timestamp,
        }

    def _call_groq(self, message: str, history: list[dict[str, str]]) -> str:
        messages = build_groq_messages(history, message)
        response = self._groq_client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.3,
            max_tokens=600,
        )
        return response.choices[0].message.content or "ขออภัย ไม่มีคำตอบในขณะนี้"


# Singleton
_chatbot: ScamGuardChatbot | None = None


def get_chatbot() -> ScamGuardChatbot:
    global _chatbot
    if _chatbot is None:
        _chatbot = ScamGuardChatbot()
    return _chatbot
