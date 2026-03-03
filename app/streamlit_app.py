"""
ScamGuard — Streamlit Frontend
ระบบตรวจจับข้อความสแปมและฟิชชิ่งสำหรับผู้สูงอายุ

Elderly-friendly design:
  - Large Thai/English fonts
  - High contrast colors
  - Simple interaction flow
  - Clear visual indicators (🟢🟡🔴)
  - Bilingual support (Thai / English)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

# Add project root to path when running standalone
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_URL = os.environ.get("API_URL", "http://localhost:8000")
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Bilingual text dictionary
# ---------------------------------------------------------------------------
CHAT_QUICK_QUESTIONS: dict = {
    "th": [
        "สแปมคืออะไร?",
        "ฟิชชิ่งคืออะไร?",
        "สังเกตข้อความอันตรายอย่างไร?",
        "ถูกหลอกให้โอนเงินแล้วทำอย่างไร?",
        "OTP คืออะไร ทำไมห้ามบอกใคร?",
        "สายด่วนแจ้งเหตุมีเบอร์อะไรบ้าง?",
    ],
    "en": [
        "What is spam?",
        "What is phishing?",
        "How to spot dangerous messages?",
        "I was scammed and sent money, what now?",
        "What is OTP and why should I never share it?",
        "What emergency hotlines should I call?",
    ],
}

TEXTS: dict = {
    "th": {
        "page_title": "ScamGuard — ตรวจสอบข้อความ",
        "sidebar_brand": "🛡️ ScamGuard",
        "sidebar_version": f"v{APP_VERSION} — ระบบตรวจสอบข้อความ",
        "stats_header": "### 📊 สถิติวันนี้",
        "stats_checked": "ตรวจแล้ว",
        "stats_danger": "พบอันตราย",
        "history_header": "### 🕐 ประวัติการตรวจ",
        "history_empty": "ยังไม่มีประวัติการตรวจ",
        "clear_history": "🗑️ ล้างประวัติ",
        "tips_header": "### 💡 วิธีสังเกตข้อความอันตราย",
        "tips": [
            "มีการเร่งรัดให้ทำอะไรบางอย่างทันที",
            "มีลิงก์หรือหมายเลขโทรศัพท์แปลกๆ",
            "มีรางวัลหรือเงินที่ไม่ได้สมัคร",
            "ขอ OTP หรือรหัสส่วนตัว",
            "อ้างชื่อธนาคารหรือหน่วยงานราชการ",
            "ขู่ว่าบัญชีจะถูกระงับหรือปิด",
        ],
        "hotline_cyber": "📞 สายด่วนไซเบอร์: **1599**",
        "hotline_bank": "📞 สายด่วนธนาคาร: โทรหลังบัตรโดยตรง",
        "main_title": "🛡️ ScamGuard",
        "subtitle": "ระบบตรวจสอบข้อความต้องสงสัย — ปกป้องคุณจากมิจฉาชีพออนไลน์",
        # ── Usage guide ──────────────────────────────────────────────────
        "guide_header": "📖 วิธีใช้งาน ScamGuard",
        "guide_subtitle": "ทำตามขั้นตอนง่ายๆ 5 ขั้นตอน เพื่อตรวจสอบข้อความที่น่าสงสัย",
        "guide_steps": [
            {
                "num": "1",
                "icon": "📨",
                "title": "รับข้อความที่น่าสงสัย",
                "body": (
                    "เมื่อท่านได้รับ <strong>SMS, LINE หรืออีเมล</strong> ที่ไม่แน่ใจ "
                    "หรือดูน่าสงสัย เช่น แจ้งรางวัล แจ้งหนี้ หรือขอรหัส "
                    "ให้หยุด <u>อย่าเพิ่งตอบหรือกดอะไร</u> ก่อนตรวจสอบ"
                ),
            },
            {
                "num": "2",
                "icon": "📋",
                "title": "คัดลอกข้อความนั้น",
                "body": (
                    "กดค้างที่ข้อความในโทรศัพท์ของท่าน จนกว่าจะมีเมนูขึ้นมา "
                    'แล้วเลือก <strong>"คัดลอก"</strong> หรือ <strong>"Copy"</strong> '
                    "<br>หากเป็นอีเมล ให้ลากคลุมข้อความทั้งหมด แล้วกด Ctrl+C (บนคอมพิวเตอร์)"
                ),
            },
            {
                "num": "3",
                "icon": "📝",
                "title": "วางข้อความในกล่องด้านล่าง",
                "body": (
                    "กดค้างในกล่องสี่เหลี่ยมสีขาวที่เขียนว่า "
                    '<em>"วางข้อความ SMS, LINE หรืออีเมลที่น่าสงสัยที่นี่..."</em> '
                    'แล้วเลือก <strong>"วาง"</strong> หรือ <strong>"Paste"</strong> '
                    "<br>บนคอมพิวเตอร์ สามารถกด <strong>Ctrl+V</strong> ได้เลย"
                ),
            },
            {
                "num": "4",
                "icon": "🔍",
                "title": 'กดปุ่ม "ตรวจสอบข้อความ"',
                "body": (
                    "กดปุ่มสีน้ำเงินขนาดใหญ่ <strong>🔍 ตรวจสอบข้อความ</strong> ด้านล่างกล่อง "
                    "รอสักครู่ (ไม่เกิน 5 วินาที) ระบบ AI จะวิเคราะห์ข้อความให้อัตโนมัติ"
                ),
            },
            {
                "num": "5",
                "icon": "📊",
                "title": "อ่านผลการตรวจสอบ",
                "body": (
                    "<span class='guide-result-safe'>✅ กรอบสีเขียว = ข้อความปลอดภัย</span> "
                    "ไม่ต้องกังวล สามารถตอบหรืออ่านได้ตามปกติ<br><br>"
                    "<span class='guide-result-warn'>⚠️ กรอบสีส้ม = สแปม (ขยะ)</span> "
                    "ข้อความรบกวน ไม่ต้องตอบ ลบทิ้งได้เลย<br><br>"
                    "<span class='guide-result-danger'>🚨 กรอบสีแดง = อันตราย (ฟิชชิ่ง)</span> "
                    "ข้อความหลอกลวง <u>อย่าตอบสนองใดๆ</u> ทั้งสิ้น"
                ),
            },
            {
                "num": "6",
                "icon": "🚔",
                "title": "ถ้าพบว่าอันตราย — ทำอย่างนี้",
                "body": (
                    "🚫 <strong>อย่ากดลิงก์</strong> ในข้อความเด็ดขาด<br>"
                    "🚫 <strong>อย่าโทรตามเบอร์</strong> ที่ส่งมา<br>"
                    "🚫 <strong>อย่าบอกรหัส OTP</strong> หรือรหัสผ่านใครทั้งนั้น<br>"
                    "📞 โทรแจ้ง <strong>สายด่วนไซเบอร์ 1599</strong> ได้ทันที (ฟรี 24 ชม.)<br>"
                    "👨‍👩‍👧 หรือ<strong>โทรหาลูกหลาน</strong>คนที่ไว้ใจได้เพื่อขอความช่วยเหลือ"
                ),
            },
        ],
        "guide_tip_box": (
            "💡 <strong>เคล็ดลับ:</strong> หากข้อความนั้นมาจากคนที่รู้จักจริง "
            "แต่ดูผิดปกติ ให้โทรถามคนนั้นโดยตรงก่อน อย่าส่งเงินหรือข้อมูลใดๆ "
            "จนกว่าจะมั่นใจ 100%"
        ),
        # ─────────────────────────────────────────────────────────────────
        "input_header": "### 📩 วางข้อความที่ต้องการตรวจสอบ",
        "input_placeholder": (
            "วางข้อความ SMS, LINE, หรืออีเมลที่น่าสงสัยที่นี่...\n\n"
            "ตัวอย่าง: ยินดีด้วยคุณได้รับรางวัล 50,000 บาท กดลิงก์เพื่อรับรางวัล bit.ly/claim"
        ),
        "examples_expander": "📋 ดูตัวอย่างข้อความสำหรับทดสอบ",
        "examples_header": "**ตัวอย่างข้อความ (คลิกเพื่อคัดลอก):**",
        "examples": {
            "⚠️ สแปมรางวัล": "ยินดีด้วยคุณได้รับรางวัล 100,000 บาท กดลิงก์เพื่อรับรางวัลก่อนหมดเวลา: bit.ly/reward-th",
            "🚨 ฟิชชิ่งธนาคาร": "แจ้งเตือนจากธนาคารกสิกรไทย บัญชีของท่านพบรายการผิดปกติ กรุณายืนยัน OTP: 456789 ภายใน 5 นาที",
            "🚨 ฟิชชิ่งตำรวจ": "เจ้าหน้าที่ตำรวจไซเบอร์แจ้ง บัญชีของท่านเกี่ยวข้องกับคดีฟอกเงิน โทร 062-345-6789 ทันที",
            "✅ ข้อความปกติ": "สวัสดีครับ วันนี้จะกลับบ้านช้าหน่อย รอหน่อยนะครับ",
        },
        "btn_analyze": "🔍 ตรวจสอบข้อความ",
        "btn_analyze_help": "กดเพื่อวิเคราะห์ข้อความด้วย AI",
        "btn_clear": "🗑️ ล้าง",
        "warn_empty": "⚠️ กรุณาพิมพ์หรือวางข้อความที่ต้องการตรวจสอบก่อน",
        "spinner": "🔄 กำลังวิเคราะห์ข้อความ...",
        "result_header": "### 🔎 ผลการตรวจสอบ",
        "result_reason_label": "📝 <strong>เหตุผล:</strong>",
        "metric_confidence": "ความเชื่อมั่น",
        "metric_risk": "ระดับความเสี่ยง",
        "metric_time": "เวลาประมวลผล",
        "keywords_label": "**🔑 คำสำคัญที่พบ:**",
        "prob_expander": "📊 ดูรายละเอียดความน่าจะเป็น",
        "prob_labels": [
            ("ham", "ปกติ", "✅"),
            ("spam", "สแปม", "⚠️"),
            ("phishing", "ฟิชชิ่ง", "🚨"),
        ],
        "label_map": {"ham": "ข้อความปกติ", "spam": "สแปม", "phishing": "ฟิชชิ่ง"},
        "safety_warning": (
            "**⚠️ คำแนะนำด้านความปลอดภัย:**\n"
            "- 🚫 อย่ากดลิงก์หรือโทรไปยังหมายเลขในข้อความ\n"
            "- 🚫 อย่าให้ข้อมูลส่วนตัว รหัส OTP หรือรหัสผ่านใดๆ\n"
            "- 📞 หากสงสัย ให้โทรหาลูกหลานหรือคนที่ไว้ใจได้ก่อน\n"
            "- 🚔 แจ้งความได้ที่สายด่วน 1599 (ตำรวจไซเบอร์)"
        ),
        "feedback_header": "**💬 ผลลัพธ์ไม่ถูกต้องหรือไม่?**",
        "feedback_select_label": "เลือกคำตอบที่ถูกต้อง:",
        "feedback_placeholder": "-- กรุณาเลือก --",
        "feedback_options": [
            "",
            "ham (ข้อความปกติ)",
            "spam (สแปม)",
            "phishing (ฟิชชิ่ง)",
        ],
        "btn_feedback": "📤 ส่งความคิดเห็น",
        "feedback_success": "✅ ขอบคุณสำหรับข้อเสนอแนะ จะนำไปปรับปรุงระบบ",
        "feedback_fail": "ไม่สามารถบันทึกความคิดเห็นได้ในขณะนี้",
        "footer": (
            "🛡️ <strong>ScamGuard</strong> v1.0.0 &nbsp;|&nbsp;"
            " ระบบ AI ตรวจจับข้อความอันตรายสำหรับผู้สูงอายุ &nbsp;|&nbsp;"
            " 📞 สายด่วนไซเบอร์ <strong>1599</strong>"
        ),
        "err_timeout": "⏱️ การเชื่อมต่อใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง",
        "err_no_model": (
            "❌ ยังไม่พบโมเดล กรุณา train โมเดลก่อนใช้งาน:\n"
            "```\npython -m src.models.trainer\n```"
        ),
        # ── Chatbot tab ───────────────────────────────────────────────────
        "tab_check": "🔍 ตรวจสอบข้อความ",
        "tab_chat": "💬 ถามตอบ AI",
        "chat_title": "💬 ถามตอบกับน้องการ์ด",
        "chat_subtitle": "ถามได้เลย! เรื่องสแปม ฟิชชิ่ง วิธีรับมือ หรือสิ่งที่ต้องทำเมื่อถูกหลอก",
        "chat_quick_header": "**คำถามที่พบบ่อย (กดเพื่อถาม):**",
        "chat_input_placeholder": "พิมพ์คำถามของคุณที่นี่... เช่น ฟิชชิ่งคืออะไร หรือ ถูกหลอกให้โอนเงินต้องทำอย่างไร",
        "chat_send_btn": "📤 ส่ง",
        "chat_clear_btn": "🗑️ ล้างการสนทนา",
        "chat_thinking": "🤔 กำลังคิด...",
        "chat_empty": "ยังไม่มีการสนทนา — ลองกดคำถามด้านบน หรือพิมพ์คำถามของคุณ",
        "chat_you": "คุณ",
        "chat_bot": "น้องการ์ด",
        "chat_err_empty": "⚠️ กรุณาพิมพ์คำถามก่อน",
        "chat_err_fail": "⏱️ ไม่สามารถตอบได้ในขณะนี้ กรุณาลองใหม่",
        "chat_hotline_remind": "📞 หากเป็นเรื่องเร่งด่วน โทร **1599** (สายด่วนไซเบอร์) ได้เลย",
    },
    "en": {
        "page_title": "ScamGuard — Message Checker",
        "sidebar_brand": "🛡️ ScamGuard",
        "sidebar_version": f"v{APP_VERSION} — Message Checker",
        "stats_header": "### 📊 Today's Stats",
        "stats_checked": "Checked",
        "stats_danger": "Threats Found",
        "history_header": "### 🕐 Check History",
        "history_empty": "No history yet",
        "clear_history": "🗑️ Clear History",
        "tips_header": "### 💡 How to Spot Dangerous Messages",
        "tips": [
            "Creates urgency — demands immediate action",
            "Contains suspicious links or phone numbers",
            "Offers prizes or money you didn't sign up for",
            "Asks for OTP codes or personal passwords",
            "Impersonates a bank or government agency",
            "Threatens to suspend or close your account",
        ],
        "hotline_cyber": "📞 Cyber Hotline: **1599**",
        "hotline_bank": "📞 Bank Hotline: Call the number on the back of your card",
        "main_title": "🛡️ ScamGuard",
        "subtitle": "AI-powered message checker — protecting you from online scams",
        # ── Usage guide ──────────────────────────────────────────────────
        "guide_header": "📖 How to Use ScamGuard",
        "guide_subtitle": "Follow these simple 6 steps to check any suspicious message",
        "guide_steps": [
            {
                "num": "1",
                "icon": "📨",
                "title": "Receive a suspicious message",
                "body": (
                    "When you receive an <strong>SMS, LINE message, or email</strong> "
                    "that seems unusual — like winning a prize, debt notices, or requests for a code — "
                    "<u>stop and do not reply or click anything</u> until you check it here first."
                ),
            },
            {
                "num": "2",
                "icon": "📋",
                "title": "Copy that message",
                "body": (
                    "Press and hold the message on your phone until a menu appears, "
                    'then tap <strong>"Copy"</strong>. '
                    "<br>On a computer, select all the text and press <strong>Ctrl+C</strong>."
                ),
            },
            {
                "num": "3",
                "icon": "📝",
                "title": "Paste the message in the box below",
                "body": (
                    "Press and hold inside the white box that says "
                    '<em>"Paste a suspicious SMS, LINE message, or email here..."</em> '
                    'then tap <strong>"Paste"</strong>. '
                    "<br>On a computer, press <strong>Ctrl+V</strong>."
                ),
            },
            {
                "num": "4",
                "icon": "🔍",
                "title": 'Press the "Check Message" button',
                "body": (
                    "Tap the large blue button <strong>🔍 Check Message</strong> below the box. "
                    "Wait a moment (up to 5 seconds) — the AI will analyze it automatically."
                ),
            },
            {
                "num": "5",
                "icon": "📊",
                "title": "Read the result",
                "body": (
                    "<span class='guide-result-safe'>✅ Green box = Safe message</span> "
                    "No need to worry — you can read and reply normally.<br><br>"
                    "<span class='guide-result-warn'>⚠️ Orange box = Spam (junk)</span> "
                    "Unwanted message — no need to reply, just delete it.<br><br>"
                    "<span class='guide-result-danger'>🚨 Red box = Dangerous (Phishing)</span> "
                    "Scam message — <u>do not respond in any way</u>."
                ),
            },
            {
                "num": "6",
                "icon": "🚔",
                "title": "If it's dangerous — do this",
                "body": (
                    "🚫 <strong>Do NOT click any links</strong> in the message<br>"
                    "🚫 <strong>Do NOT call any phone numbers</strong> from the message<br>"
                    "🚫 <strong>Do NOT share OTP codes</strong> or passwords with anyone<br>"
                    "📞 Call the <strong>Cyber Crime Hotline: 1599</strong> (free, 24 hours)<br>"
                    "👨‍👩‍👧 Or <strong>call a trusted family member</strong> for help"
                ),
            },
        ],
        "guide_tip_box": (
            "💡 <strong>Tip:</strong> If the message appears to come from someone you know "
            "but seems unusual, call that person directly to confirm. "
            "Never send money or personal information until you are 100% sure."
        ),
        # ─────────────────────────────────────────────────────────────────
        "input_header": "### 📩 Paste the message you want to check",
        "input_placeholder": (
            "Paste a suspicious SMS, LINE message, or email here...\n\n"
            "Example: Congratulations! You've won 50,000 Baht. Click to claim: bit.ly/claim"
        ),
        "examples_expander": "📋 View example messages for testing",
        "examples_header": "**Example messages (click to copy):**",
        "examples": {
            "⚠️ Spam — Prize": "ยินดีด้วยคุณได้รับรางวัล 100,000 บาท กดลิงก์เพื่อรับรางวัลก่อนหมดเวลา: bit.ly/reward-th",
            "🚨 Phishing — Bank": "แจ้งเตือนจากธนาคารกสิกรไทย บัญชีของท่านพบรายการผิดปกติ กรุณายืนยัน OTP: 456789 ภายใน 5 นาที",
            "🚨 Phishing — Police": "เจ้าหน้าที่ตำรวจไซเบอร์แจ้ง บัญชีของท่านเกี่ยวข้องกับคดีฟอกเงิน โทร 062-345-6789 ทันที",
            "✅ Safe message": "สวัสดีครับ วันนี้จะกลับบ้านช้าหน่อย รอหน่อยนะครับ",
        },
        "btn_analyze": "🔍 Check Message",
        "btn_analyze_help": "Click to analyze the message with AI",
        "btn_clear": "🗑️ Clear",
        "warn_empty": "⚠️ Please type or paste a message to check first",
        "spinner": "🔄 Analyzing message...",
        "result_header": "### 🔎 Analysis Result",
        "result_reason_label": "📝 <strong>Reason:</strong>",
        "metric_confidence": "Confidence",
        "metric_risk": "Risk Level",
        "metric_time": "Processing Time",
        "keywords_label": "**🔑 Keywords Found:**",
        "prob_expander": "📊 View probability breakdown",
        "prob_labels": [
            ("ham", "Safe", "✅"),
            ("spam", "Spam", "⚠️"),
            ("phishing", "Phishing", "🚨"),
        ],
        "label_map": {"ham": "Safe", "spam": "Spam", "phishing": "Phishing"},
        "safety_warning": (
            "**⚠️ Safety Advice:**\n"
            "- 🚫 Do not click links or call numbers in the message\n"
            "- 🚫 Do not share personal info, OTP codes, or passwords\n"
            "- 📞 If in doubt, contact a trusted family member first\n"
            "- 🚔 Report to Cyber Police Hotline: 1599"
        ),
        "feedback_header": "**💬 Was the result incorrect?**",
        "feedback_select_label": "Select the correct answer:",
        "feedback_placeholder": "-- Please select --",
        "feedback_options": [
            "",
            "ham (Safe message)",
            "spam (Spam)",
            "phishing (Phishing)",
        ],
        "btn_feedback": "📤 Submit Feedback",
        "feedback_success": "✅ Thank you for your feedback! It will help improve the system.",
        "feedback_fail": "Could not save feedback at this time.",
        "footer": (
            "🛡️ <strong>ScamGuard</strong> v1.0.0 &nbsp;|&nbsp;"
            " AI-powered spam & phishing detection for the elderly &nbsp;|&nbsp;"
            " 📞 Cyber Hotline <strong>1599</strong>"
        ),
        "err_timeout": "⏱️ Connection timed out. Please try again.",
        "err_no_model": (
            "❌ Model not found. Please train the model first:\n"
            "```\npython -m src.models.trainer\n```"
        ),
        # ── Chatbot tab ───────────────────────────────────────────────────
        "tab_check": "🔍 Check Message",
        "tab_chat": "💬 Ask AI",
        "chat_title": "💬 Chat with Guardian",
        "chat_subtitle": "Ask me anything about spam, phishing, how to stay safe, or what to do if you've been scammed.",
        "chat_quick_header": "**Frequently asked questions (tap to ask):**",
        "chat_input_placeholder": "Type your question here... e.g. What is phishing? or I was scammed, what should I do?",
        "chat_send_btn": "📤 Send",
        "chat_clear_btn": "🗑️ Clear Chat",
        "chat_thinking": "🤔 Thinking...",
        "chat_empty": "No conversation yet — tap a question above or type your own.",
        "chat_you": "You",
        "chat_bot": "Guardian",
        "chat_err_empty": "⚠️ Please type a question first.",
        "chat_err_fail": "⏱️ Could not get a response right now. Please try again.",
        "chat_hotline_remind": "📞 For urgent matters, call the **Cyber Hotline: 1599** (free, 24/7)",
    },
}

# ---------------------------------------------------------------------------
# Page configuration (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ScamGuard — ตรวจสอบข้อความ",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "ScamGuard v1.0.0 — AI spam & phishing detection for the elderly",
    },
)

# ---------------------------------------------------------------------------
# Custom CSS — Large fonts, high contrast, elderly-friendly + hide toolbar
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    /* ── Hide Deploy button + 3-dot menu (Streamlit 1.54) ── */
    [data-testid="stHeaderActionElements"] { display: none !important; }
    [data-testid="stToolbar"]           { display: none !important; }
    [data-testid="stToolbarActions"]    { display: none !important; }
    [data-testid="stDecoration"]        { display: none !important; }
    [data-testid="stStatusWidget"]      { display: none !important; }
    #MainMenu                           { display: none !important; }
    .stDeployButton                     { display: none !important; }
    button[kind="header"]               { display: none !important; }

    /* ── Hide sidebar entirely ── */
    [data-testid="stSidebar"]          { display: none !important; }
    section[data-testid="stSidebar"]   { display: none !important; }
    [data-testid="stSidebarNav"]       { display: none !important; }
    [data-testid="collapsedControl"]   { display: none !important; }

    /* ── Wide layout with generous desktop space ── */
    .block-container {
        max-width: 1400px !important;
        width: 96% !important;
        margin: 0 auto !important;
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    @media (max-width: 1280px) {
        .block-container { max-width: 1100px !important; }
    }

    @media (max-width: 1024px) {
        .block-container { max-width: 900px !important; }
    }

    @media (max-width: 768px) {
        .block-container {
            width: 100% !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }
    }

    /* ── Base font size for elderly ── */
    html, body, [class*="css"] {
        font-size: 18px !important;
    }

    /* ── Main title (fallback when no logo) ── */
    .main-title {
        font-size: 2.8rem !important;
        font-weight: 900 !important;
        color: #1a237e !important;
        text-align: center;
        padding: 1rem 0 0.5rem 0;
        font-family: 'Sarabun', 'Tahoma', sans-serif;
    }

    .subtitle {
        font-size: 1.3rem !important;
        color: #37474f !important;
        text-align: center;
        padding-bottom: 1.5rem;
    }

    /* ── Logo header ── */
    .logo-header-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.5rem 0 0.3rem 0;
    }

    /* ── Subtitle under logo ── */
    .logo-subtitle {
        font-size: 1.15rem !important;
        color: #546e7a !important;
        text-align: center;
        padding-bottom: 0.8rem;
        font-family: 'Sarabun', 'Tahoma', sans-serif;
    }

    /* ── Usage Guide ── */
    .guide-container {
        background-color: #f0f4ff;
        border: 2px solid #3949ab;
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin: 1rem 0 1.5rem 0;
    }

    .guide-header {
        font-size: 1.6rem !important;
        font-weight: 900 !important;
        color: #1a237e;
        margin-bottom: 0.3rem;
    }

    .guide-subtitle {
        font-size: 1.05rem;
        color: #546e7a;
        margin-bottom: 1.2rem;
    }

    .guide-step {
        background-color: #ffffff;
        border: 2px solid #c5cae9;
        border-radius: 12px;
        padding: 1rem 1.3rem;
        margin: 0.7rem 0;
        display: flex;
        align-items: flex-start;
        gap: 1rem;
    }

    .guide-step-num {
        background-color: #1a237e;
        color: #ffffff;
        border-radius: 50%;
        width: 2.2rem;
        height: 2.2rem;
        min-width: 2.2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        font-weight: 900;
    }

    .guide-step-icon {
        font-size: 1.8rem;
        min-width: 2rem;
        text-align: center;
        line-height: 1;
    }

    .guide-step-body h4 {
        font-size: 1.15rem;
        font-weight: 800;
        color: #1a237e;
        margin: 0 0 0.4rem 0;
    }

    .guide-step-body p {
        font-size: 1.05rem;
        color: #37474f;
        margin: 0;
        line-height: 1.8;
    }

    .guide-result-safe {
        background-color: #e8f5e9;
        border: 2px solid #2e7d32;
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        font-weight: 700;
        color: #1b5e20;
        display: inline-block;
        margin-bottom: 0.3rem;
    }

    .guide-result-warn {
        background-color: #fff8e1;
        border: 2px solid #f57f17;
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        font-weight: 700;
        color: #e65100;
        display: inline-block;
        margin-bottom: 0.3rem;
    }

    .guide-result-danger {
        background-color: #ffebee;
        border: 2px solid #c62828;
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        font-weight: 700;
        color: #b71c1c;
        display: inline-block;
        margin-bottom: 0.3rem;
    }

    .guide-tip {
        background-color: #fff9c4;
        border-left: 5px solid #f9a825;
        border-radius: 8px;
        padding: 0.9rem 1.2rem;
        margin-top: 1rem;
        font-size: 1.05rem;
        line-height: 1.7;
        color: #37474f;
    }

    /* ── Result cards ── */
    .result-safe {
        background-color: #e8f5e9;
        border: 3px solid #2e7d32;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .result-danger {
        background-color: #ffebee;
        border: 3px solid #c62828;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    .result-title {
        font-size: 2rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem;
    }

    .result-explanation {
        font-size: 1.2rem !important;
        margin-top: 0.5rem;
        line-height: 1.8;
    }

    /* ── Buttons ── */
    .stButton > button {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        padding: 0.8rem 2rem !important;
        border-radius: 10px !important;
        width: 100%;
    }

    /* ── Text area ── */
    .stTextArea > label {
        font-size: 1.3rem !important;
        font-weight: 700 !important;
    }

    textarea {
        font-size: 1.2rem !important;
        line-height: 1.7 !important;
    }

    /* ── Sidebar ── */
    .sidebar-title {
        font-size: 1.4rem !important;
        font-weight: 800 !important;
        color: #1a237e;
        border-bottom: 2px solid #1a237e;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }

    .tip-box {
        background-color: #e3f2fd;
        border-left: 4px solid #1976d2;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        font-size: 1rem;
        line-height: 1.6;
    }

    .history-item {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin: 0.4rem 0;
        font-size: 0.95rem;
    }

    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background-color: #f5f5f5;
        border-radius: 10px;
        padding: 0.8rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 900 !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        padding: 0.7rem 1.5rem !important;
    }

    /* ══════════════════════════════════════════
       LINE-like Chat UI
    ══════════════════════════════════════════ */

    /* LINE header bar */
    .line-chat-header {
        background: linear-gradient(135deg, #06C755 0%, #00A040 100%);
        color: white;
        border-radius: 20px;
        padding: 1rem 1.4rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(6, 199, 85, 0.35);
    }

    .line-chat-avatar-wrap {
        background: white;
        border-radius: 50%;
        width: 3.2rem;
        height: 3.2rem;
        min-width: 3.2rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }

    .line-chat-name {
        font-size: 1.25rem;
        font-weight: 900;
        line-height: 1.3;
    }

    .line-chat-status {
        font-size: 0.9rem;
        opacity: 0.92;
        margin-top: 0.1rem;
    }

    .line-chat-badge {
        margin-left: auto;
        background: rgba(255,255,255,0.25);
        border-radius: 10px;
        padding: 0.2rem 0.6rem;
        font-size: 0.8rem;
        font-weight: 700;
        white-space: nowrap;
    }

    /* Quick question pills */
    div[data-testid="stHorizontalBlock"] .stButton > button {
        border-radius: 20px !important;
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        padding: 0.35rem 0.8rem !important;
        background: white !important;
        color: #00A040 !important;
        border: 2px solid #06C755 !important;
        box-shadow: 0 1px 4px rgba(6,199,85,0.15) !important;
        transition: all 0.15s ease;
    }

    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        background: #06C755 !important;
        color: white !important;
    }

    /* User chat bubble — right, LINE green */
    .line-user-wrap {
        display: flex;
        justify-content: flex-end;
        margin: 0.15rem 0;
    }

    .line-bubble-user {
        background: #06C755;
        color: #ffffff;
        border-radius: 18px 18px 4px 18px;
        padding: 0.75rem 1.1rem;
        font-size: 1.1rem;
        line-height: 1.7;
        max-width: 82%;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(6,199,85,0.28);
        display: inline-block;
        text-align: left;
    }

    /* Bot chat bubble — left, white */
    .line-bot-wrap {
        display: flex;
        justify-content: flex-start;
        margin: 0.15rem 0;
    }

    .line-bubble-bot {
        background: #ffffff;
        color: #333333;
        border-radius: 4px 18px 18px 18px;
        padding: 0.75rem 1.1rem;
        font-size: 1.1rem;
        line-height: 1.8;
        max-width: 88%;
        word-wrap: break-word;
        border: 1.5px solid #E8E8E8;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        display: inline-block;
    }

    /* Override Streamlit chat message chrome */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        padding: 0.15rem 0 !important;
        gap: 0.6rem !important;
    }

    [data-testid="stChatMessageContent"] {
        background: transparent !important;
        padding: 0 !important;
    }

    /* Hide user person icon */
    [data-testid="stChatMessageAvatarUser"] {
        display: none !important;
    }

    /* Larger bot avatar circle */
    [data-testid="stChatMessageAvatarAssistant"] {
        width: 3rem !important;
        height: 3rem !important;
        min-width: 3rem !important;
        font-size: 1.6rem !important;
        line-height: 3rem !important;
        border-radius: 50% !important;
    }

    /* Empty state */
    .chat-empty-state {
        text-align: center;
        color: #9e9e9e;
        padding: 3rem 1rem;
        font-size: 1rem;
    }

    .chat-empty-state .chat-empty-icon {
        font-size: 3.5rem;
        margin-bottom: 0.5rem;
    }

    /* ── Language toggle — fixed top-right ── */
    .lang-toggle-wrap {
        position: fixed;
        top: 14px;
        right: 20px;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.96);
        border-radius: 24px;
        padding: 5px 16px;
        box-shadow: 0 2px 14px rgba(0, 0, 0, 0.12);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 0, 0, 0.07);
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: 'Sarabun', 'Tahoma', sans-serif;
    }

    .lang-active {
        color: #1a237e;
        font-weight: 800;
        font-size: 0.92rem;
    }

    .lang-link {
        color: #9e9e9e;
        text-decoration: none;
        font-weight: 500;
        font-size: 0.92rem;
        transition: color 0.2s ease;
    }

    .lang-link:hover { color: #1a237e; }

    .lang-divider { color: #ddd; font-weight: 300; }

    /* Tablet */
    @media (max-width: 1024px) {
        .lang-toggle-wrap { top: 10px; right: 14px; padding: 5px 14px; }
    }

    /* Mobile */
    @media (max-width: 768px) {
        .lang-toggle-wrap { top: 8px; right: 10px; padding: 4px 11px; }
        .lang-active, .lang-link { font-size: 0.8rem !important; }
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []
if "total_checked" not in st.session_state:
    st.session_state.total_checked = 0
if "spam_found" not in st.session_state:
    st.session_state.spam_found = 0
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = False
if "lang" not in st.session_state:
    st.session_state.lang = "th"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = (
        []
    )  # [{"role": "user"|"assistant", "content": "..."}]
if "chat_input_prefill" not in st.session_state:
    st.session_state.chat_input_prefill = ""
if "_chat_pending" not in st.session_state:
    st.session_state._chat_pending = None  # prompt waiting for API response

# Read language from URL query param (?lang=th or ?lang=en)
_qp = st.query_params
if "lang" in _qp and _qp["lang"] in ("th", "en"):
    st.session_state.lang = _qp["lang"]

# T is resolved once per run from session_state.lang
T = TEXTS[st.session_state.lang]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def call_predict_api(text: str, T: dict) -> dict | None:
    """Call the FastAPI prediction endpoint."""
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json={"text": text},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return _predict_local(text, T)
    except requests.exceptions.Timeout:
        st.error(T["err_timeout"])
        return None
    except Exception:
        return _predict_local(text, T)


def _predict_local(text: str, T: dict) -> dict | None:
    """Direct local prediction fallback (no API server required)."""
    try:
        from src.models.predictor import get_predictor

        predictor = get_predictor()
        return predictor.predict(text)
    except FileNotFoundError:
        st.error(T["err_no_model"])
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def get_api_stats() -> dict | None:
    """Fetch prediction statistics from API."""
    try:
        response = requests.get(f"{API_URL}/stats", timeout=5)
        return response.json()
    except Exception:
        return None


def submit_feedback(text: str, predicted: str, actual: str) -> bool:
    """Submit user feedback to the API."""
    try:
        response = requests.post(
            f"{API_URL}/feedback",
            json={"text": text, "predicted_label": predicted, "actual_label": actual},
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def call_chat_api(message: str, history: list[dict], T: dict) -> str | None:
    """เรียก /chat endpoint หรือ local chatbot fallback"""
    payload = {
        "message": message,
        "history": history[-10:],
    }
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("reply", "")
    except requests.exceptions.ConnectionError:
        return _chat_local(message, history)
    except requests.exceptions.Timeout:
        st.error(T["chat_err_fail"])
        return None
    except Exception:
        return _chat_local(message, history)


def _chat_local(message: str, history: list[dict]) -> str | None:
    """Local chatbot fallback (ไม่ต้องใช้ API server)"""
    try:
        from src.api.chatbot import get_chatbot

        bot = get_chatbot()
        result = bot.chat(message=message, history=history)
        return result["reply"]
    except Exception as exc:
        return f"ขออภัย เกิดข้อผิดพลาด: {exc}"


def _escape_html(text: str) -> str:
    """Escape user-provided text ป้องกัน XSS ใน chat bubble"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "<br>")
    )


def _md_to_html(text: str) -> str:
    """แปลง markdown เบื้องต้น → HTML สำหรับ bot bubble (trusted source)"""
    import re as _re

    text = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = _re.sub(r"\*([^*\n]+?)\*", r"<em>\1</em>", text)
    text = text.replace("\n", "<br>")
    return text


def render_guide(T: dict) -> None:
    """Render the step-by-step usage guide for elderly users."""
    # Build HTML as a list of strings to avoid f-string nesting issues
    parts = [
        '<div class="guide-container">',
        '<div class="guide-header">' + T["guide_header"] + "</div>",
        '<div class="guide-subtitle">' + T["guide_subtitle"] + "</div>",
    ]
    for step in T["guide_steps"]:
        parts += [
            '<div class="guide-step">',
            '<div class="guide-step-num">' + step["num"] + "</div>",
            '<div class="guide-step-icon">' + step["icon"] + "</div>",
            '<div class="guide-step-body">',
            "<h4>" + step["title"] + "</h4>",
            "<p>" + step["body"] + "</p>",
            "</div></div>",
        ]
    parts += [
        '<div class="guide-tip">' + T["guide_tip_box"] + "</div>",
        "</div>",
    ]
    st.markdown("\n".join(parts), unsafe_allow_html=True)


def display_result(result: dict, original_text: str, T: dict) -> None:
    """Render prediction result with color coding and explanation."""
    label = result["label"]
    label_th = result["label_th"]
    confidence = result["confidence"]
    risk_level = result["risk_level"]
    explanation = result["explanation"]
    keywords = result.get("keywords", [])
    probabilities = result.get("probabilities", {})

    if label == "ham":
        card_class = "result-safe"
        emoji = "✅"
        title_color = "#1b5e20"
    elif label == "spam":
        card_class = "result-danger"
        emoji = "⚠️"
        title_color = "#b71c1c"
    else:  # phishing
        card_class = "result-danger"
        emoji = "🚨"
        title_color = "#880e4f"

    # Main result card
    st.markdown(
        f"""
    <div class="{card_class}">
        <div class="result-title" style="color: {title_color};">
            {emoji} &nbsp; {label_th.upper()}
        </div>
        <div class="result-explanation">
            {T["result_reason_label"]} {explanation}
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label=T["metric_confidence"],
            value=f"{confidence * 100:.1f}%",
        )
    with col2:
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk_level, "⚪")
        st.metric(
            label=T["metric_risk"],
            value=f"{risk_emoji} {result.get('risk_level_th', risk_level)}",
        )
    with col3:
        st.metric(
            label=T["metric_time"],
            value=f"{result.get('processing_time_ms', 0):.0f} ms",
        )

    # Keywords
    if keywords:
        st.markdown(
            T["keywords_label"] + " " + " • ".join([f"`{kw}`" for kw in keywords])
        )

    # Probability breakdown
    with st.expander(T["prob_expander"]):
        cols = st.columns(3)
        for i, (lbl, lbl_display, icon) in enumerate(T["prob_labels"]):
            with cols[i]:
                pct = probabilities.get(lbl, 0) * 100
                st.progress(pct / 100)
                st.caption(f"{icon} {lbl_display}: **{pct:.1f}%**")

    # Warning advice for dangerous messages
    if label != "ham":
        st.warning(T["safety_warning"])

    # Feedback section
    st.markdown("---")
    st.markdown(T["feedback_header"])
    correct_label = st.selectbox(
        T["feedback_select_label"],
        options=T["feedback_options"],
        format_func=lambda x: T["feedback_placeholder"] if x == "" else x,
        key=f"feedback_select_{hash(original_text)}",
    )
    if correct_label and correct_label != "":
        actual = correct_label.split(" ")[0]
        if st.button(T["btn_feedback"], key=f"feedback_btn_{hash(original_text)}"):
            if submit_feedback(original_text, label, actual):
                st.success(T["feedback_success"])
            else:
                st.warning(T["feedback_fail"])


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

# ── Fixed top-right language toggle (position: fixed via CSS) ─────────────
_is_th = st.session_state.lang == "th"
st.markdown(
    f"""
    <div class="lang-toggle-wrap">
        {'<strong class="lang-active">ไทย</strong>' if _is_th else '<a href="?lang=th" class="lang-link">ไทย</a>'}
        <span class="lang-divider">|</span>
        {'<a href="?lang=en" class="lang-link">English</a>' if _is_th else '<strong class="lang-active">English</strong>'}
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Logo header ───────────────────────────────────────────────────────────
_LOGO_PATH = Path(__file__).parent / "assets" / "scamguard_logo.png"

if _LOGO_PATH.exists():
    _lcol, _mcol, _rcol = st.columns([1, 2, 1])
    with _mcol:
        st.image(str(_LOGO_PATH), use_container_width=True)
else:
    st.markdown(
        f'<div class="main-title">{T["main_title"]}</div>', unsafe_allow_html=True
    )

st.markdown(
    f'<div class="logo-subtitle">{T["subtitle"]}</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────
tab_check, tab_chat = st.tabs([T["tab_check"], T["tab_chat"]])

# ===========================================================================
# Tab 1: ตรวจสอบข้อความ
# ===========================================================================
with tab_check:
    # ── Usage Guide ───────────────────────────────────────────────────────
    render_guide(T)

    st.markdown("---")

    # Input area
    st.markdown(T["input_header"])
    user_input = st.text_area(
        label="message",
        placeholder=T["input_placeholder"],
        height=160,
        label_visibility="collapsed",
        key="user_input_area",
    )

    # Quick test examples
    with st.expander(T["examples_expander"]):
        st.markdown(T["examples_header"])
        cols = st.columns(2)
        for i, (label, text) in enumerate(T["examples"].items()):
            with cols[i % 2]:
                st.code(text, language=None)

    # Analyze button
    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        analyze_clicked = st.button(
            T["btn_analyze"],
            type="primary",
            use_container_width=True,
            help=T["btn_analyze_help"],
        )
    with col_btn2:
        clear_clicked = st.button(
            T["btn_clear"],
            use_container_width=True,
        )

    if clear_clicked:
        st.rerun()

    # Run prediction
    if analyze_clicked:
        if not user_input or not user_input.strip():
            st.warning(T["warn_empty"])
        else:
            with st.spinner(T["spinner"]):
                result = call_predict_api(user_input.strip(), T)

            if result:
                st.markdown("---")
                st.markdown(T["result_header"])
                display_result(result, user_input.strip(), T)

                # Update session state
                st.session_state.total_checked += 1
                if result["label"] != "ham":
                    st.session_state.spam_found += 1

                # Add to history
                st.session_state.history.append(
                    {
                        "text": user_input.strip(),
                        "label": result["label"],
                        "label_th": result["label_th"],
                        "confidence": result["confidence"],
                        "timestamp": datetime.now().strftime("%H:%M"),
                    }
                )

# ===========================================================================
# Tab 2: ถามตอบ AI (Chatbot) — LINE-like UI
# ===========================================================================
with tab_chat:
    lang = st.session_state.lang
    online_txt = (
        "🟢 ออนไลน์ — ถามได้เลยครับ/ค่ะ"
        if lang == "th"
        else "🟢 Online — Ask me anything"
    )

    # ── LINE-like header ──────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="line-chat-header">
            <div class="line-chat-avatar-wrap">🛡️</div>
            <div>
                <div class="line-chat-name">{T["chat_bot"]}</div>
                <div class="line-chat-status">{online_txt}</div>
            </div>
            <div class="line-chat-badge">ScamGuard AI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Quick-question pills ──────────────────────────────────────────────
    st.markdown(T["chat_quick_header"])
    quick_questions = CHAT_QUICK_QUESTIONS[lang]
    btn_cols = st.columns(3)
    for idx, q in enumerate(quick_questions):
        with btn_cols[idx % 3]:
            if st.button(q, key=f"quick_q_{idx}", use_container_width=True):
                st.session_state.chat_input_prefill = q

    st.markdown("---")

    # ── Process quick-question prefill: save as pending then rerun ────────
    if st.session_state.chat_input_prefill:
        prefill = st.session_state.chat_input_prefill.strip()
        st.session_state.chat_input_prefill = ""
        st.session_state.chat_messages.append({"role": "user", "content": prefill})
        st.session_state._chat_pending = prefill
        st.rerun()

    # ── Display empty state ───────────────────────────────────────────────
    if not st.session_state.chat_messages and not st.session_state._chat_pending:
        st.markdown(
            f'<div class="chat-empty-state">'
            f'<div class="chat-empty-icon">💬</div>'
            f'{T["chat_empty"]}'
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Render all messages from session state (above chat_input) ─────────
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(
                    f'<div class="line-user-wrap">'
                    f'<div class="line-bubble-user">{_escape_html(msg["content"])}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            with st.chat_message("assistant", avatar="🛡️"):
                st.markdown(
                    f'<div class="line-bot-wrap">'
                    f'<div class="line-bubble-bot">{_md_to_html(msg["content"])}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Pending response: call API here so spinner appears above input ─────
    if st.session_state._chat_pending:
        with st.chat_message("assistant", avatar="🛡️"):
            with st.spinner(T["chat_thinking"]):
                _reply = call_chat_api(
                    st.session_state._chat_pending,
                    st.session_state.chat_messages[:-1],
                    T,
                )
        st.session_state._chat_pending = None
        if _reply:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": _reply}
            )
        else:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": T["chat_err_fail"]}
            )
        st.rerun()

    # ── Clear button (only when there are messages) ───────────────────────
    if st.session_state.chat_messages:
        if st.button(T["chat_clear_btn"], key="clear_chat_btn"):
            st.session_state.chat_messages = []
            st.rerun()

    # ── st.chat_input — pinned to bottom; save state + rerun to render above ─
    if prompt := st.chat_input(T["chat_input_placeholder"]):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        st.session_state._chat_pending = prompt
        st.rerun()

    # ── Hotline reminder ──────────────────────────────────────────────────
    st.info(T["chat_hotline_remind"])

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: #9e9e9e; font-size: 0.9rem; padding: 1rem 0;">
        {T["footer"]}
    </div>
    """,
    unsafe_allow_html=True,
)
