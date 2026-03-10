"""
ScamGuard — Streamlit Frontend (Elderly-Friendly Redesign)
ระบบตรวจสอบอีเมลและข้อความต้องสงสัย

Redesign goals (Senior Citizens 55+):
  - Font size minimum 20px throughout
  - Maximum 3-step flow
  - No technical jargon
  - Large buttons & high-contrast colors
  - Clear, plain-language result cards
  - Phishing education section on main page
  - Bilingual: Thai / English
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_URL = os.environ.get("API_URL", "http://localhost")
APP_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Bilingual text dictionary (plain-language, jargon-free)
# ---------------------------------------------------------------------------
CHAT_QUICK_QUESTIONS: dict = {
    "th": [
        "ข้อความไหนที่ต้องระวัง?",
        "ถ้าถูกหลอกให้โอนเงินต้องทำอย่างไร?",
        "OTP คืออะไร ทำไมห้ามบอกใคร?",
        "สายด่วนแจ้งเหตุโทรที่ไหน?",
        "อีเมลหลอกลวงหน้าตาเป็นอย่างไร?",
        "ลิงก์อันตรายดูอย่างไร?",
    ],
    "en": [
        "Which messages should I watch out for?",
        "I was scammed and sent money — what now?",
        "What is OTP and why should I never share it?",
        "What emergency hotline should I call?",
        "What does a scam email look like?",
        "How do I spot a dangerous link?",
    ],
}

TEXTS: dict = {
    "th": {
        # ── Page ──────────────────────────────────────────────────────────
        "page_title": "ScamGuard — ตรวจสอบความปลอดภัย",
        "main_title": "🛡️ ScamGuard",
        "subtitle": "ตรวจสอบอีเมลและข้อความต้องสงสัย — ปกป้องคุณจากมิจฉาชีพ",
        # ── Tabs ──────────────────────────────────────────────────────────
        "tab_check": "🔍  ตรวจสอบข้อความ",
        "tab_tips": "📚  วิธีสังเกตมิจฉาชีพ",
        "tab_chat": "💬  ถามตอบ AI",
        # ── 3-step guide ──────────────────────────────────────────────────
        "steps_header": "วิธีใช้งาน — 3 ขั้นตอนง่ายๆ",
        "step1_num": "1",
        "step1_icon": "📋",
        "step1_title": "คัดลอกข้อความที่น่าสงสัย",
        "step1_body": (
            "กดค้างที่ข้อความ SMS, LINE หรืออีเมลที่ดูน่าสงสัย "
            "แล้วเลือก <strong>\"คัดลอก\"</strong> หรือ <strong>\"Copy\"</strong>"
        ),
        "step2_num": "2",
        "step2_icon": "📝",
        "step2_title": "วางข้อความในช่องด้านล่าง",
        "step2_body": (
            "กดค้างในช่องข้อความด้านล่าง แล้วเลือก <strong>\"วาง\"</strong> หรือ <strong>\"Paste\"</strong> "
            "จากนั้นกดปุ่ม <strong>\"ตรวจสอบความปลอดภัย\"</strong>"
        ),
        "step3_num": "3",
        "step3_icon": "🔍",
        "step3_title": "ดูผลการตรวจสอบ",
        "step3_body": (
            "ระบบจะแสดงผลทันทีว่าข้อความนั้น "
            "<strong style='color:#2e7d32'>ปลอดภัย</strong>, "
            "<strong style='color:#e65100'>น่าสงสัย</strong> หรือ "
            "<strong style='color:#c62828'>อันตราย</strong>"
        ),
        # ── Input section ─────────────────────────────────────────────────
        "input_header": "### 📨 วางข้อความที่ต้องการตรวจสอบที่นี่",
        "input_placeholder": (
            "วางข้อความที่ได้รับที่นี่...\n\n"
            "เช่น: \"ท่านได้รับรางวัล 50,000 บาท กรุณากดลิงก์นี้เพื่อรับรางวัล\""
        ),
        "examples_expander": "📋 ดูตัวอย่างข้อความสำหรับทดสอบ",
        "examples": {
            "⚠️ สแปมรางวัล": "ยินดีด้วยคุณได้รับรางวัล 100,000 บาท กดลิงก์เพื่อรับรางวัลก่อนหมดเวลา: bit.ly/reward-th",
            "🚨 ฟิชชิ่งธนาคาร": "แจ้งเตือนจากธนาคารกสิกรไทย บัญชีของท่านพบรายการผิดปกติ กรุณายืนยัน OTP: 456789 ภายใน 5 นาที",
            "🚨 ฟิชชิ่งตำรวจ": "เจ้าหน้าที่ตำรวจไซเบอร์แจ้ง บัญชีของท่านเกี่ยวข้องกับคดีฟอกเงิน โทร 062-345-6789 ทันที",
            "✅ ข้อความปกติ": "สวัสดีครับ วันนี้จะกลับบ้านช้าหน่อย รอหน่อยนะครับ",
        },
        "btn_analyze": "🔍  ตรวจสอบความปลอดภัย",
        "btn_analyze_help": "คลิกเพื่อตรวจสอบว่าข้อความนี้ปลอดภัยหรือไม่",
        "btn_clear": "🗑️  ล้างข้อความ",
        "spinner": "กำลังตรวจสอบ กรุณารอสักครู่...",
        "warn_empty": "⚠️ กรุณาวางข้อความที่ต้องการตรวจสอบก่อน",
        "err_timeout": "⏱️ ระบบตอบสนองช้า กรุณาลองใหม่อีกครั้ง",
        "err_no_model": "❌ ไม่พบโมเดล กรุณาติดต่อผู้ดูแลระบบ",
        # ── Result section ────────────────────────────────────────────────
        "result_header": "### 📊 ผลการตรวจสอบ",
        "result_safe_title": "✅  ข้อความนี้ปลอดภัย",
        "result_spam_title": "⚠️  ข้อความนี้น่าสงสัย",
        "result_phishing_title": "🚨  ข้อความนี้อันตราย!",
        "result_safe_msg": (
            "ระบบไม่พบสัญญาณของมิจฉาชีพในข้อความนี้ "
            "แต่ควรระวังเสมอ หากไม่แน่ใจให้ถามคนในครอบครัว"
        ),
        "result_spam_msg": (
            "ข้อความนี้มีลักษณะที่น่าสงสัย อาจเป็นการโฆษณาหรือข้อความรบกวน "
            "<strong>ไม่ควรกดลิงก์หรือโทรตามเบอร์ที่ให้มา</strong>"
        ),
        "result_phishing_msg": (
            "ข้อความนี้อาจพยายาม <strong>ขโมยข้อมูลส่วนตัว</strong> หรือ "
            "<strong>หลอกให้โอนเงิน</strong> "
            "ห้ามกดลิงก์ ห้ามโทรตาม และห้ามให้รหัส OTP หรือรหัสผ่านใดๆ"
        ),
        "result_reason_label": "เหตุผล:",
        "result_keywords_label": "คำที่พบในข้อความ:",
        "result_action_safe": "💡 หากยังไม่แน่ใจ ลองถามลูกหลานหรือคนใกล้ชิดก่อน",
        "result_action_danger": (
            "🆘 หากถูกหลอกลวงไปแล้ว โทรแจ้ง <strong>สายด่วนไซเบอร์ 1599</strong> ได้ทันที (ฟรี 24 ชม.)"
        ),
        # ── Education tips tab ────────────────────────────────────────────
        "tips_page_header": "## 📚 วิธีสังเกตอีเมลและข้อความหลอกลวง",
        "tips_intro": (
            "มิจฉาชีพมักส่งข้อความที่ดูเหมือนมาจากธนาคาร หน่วยงานราชการ "
            "หรือบริษัทที่น่าเชื่อถือ เพื่อหลอกเอาข้อมูลส่วนตัวหรือเงิน "
            "สังเกตสัญญาณเตือนเหล่านี้:"
        ),
        "warning_signs": [
            {
                "icon": "⏰",
                "title": "เร่งรัดให้ทำทันที",
                "body": (
                    "\"ด่วน!\", \"วันนี้วันสุดท้าย\", \"บัญชีจะถูกปิดใน 24 ชั่วโมง\" "
                    "— มิจฉาชีพกดดันให้รีบทำโดยไม่ทันคิด"
                ),
            },
            {
                "icon": "🎁",
                "title": "รางวัลหรือเงินที่ไม่ได้สมัคร",
                "body": (
                    "\"คุณได้รับรางวัล 100,000 บาท\" หรือ \"คุณถูกเลือกเป็นผู้โชคดี\" "
                    "— ของที่ได้มาง่ายๆ มักไม่มีจริง"
                ),
            },
            {
                "icon": "🔐",
                "title": "ขอรหัส OTP หรือรหัสผ่าน",
                "body": (
                    "ธนาคารและหน่วยงานราชการที่แท้จริง <strong>จะไม่มีวันขอรหัส OTP</strong> "
                    "หรือรหัสผ่านจากคุณทางโทรศัพท์หรือข้อความ"
                ),
            },
            {
                "icon": "🔗",
                "title": "ลิงก์หรือเบอร์โทรแปลกๆ",
                "body": (
                    "ลิงก์ที่มีตัวเลขและอักขระแปลกๆ เช่น bit.ly/... หรือ "
                    "เบอร์โทรที่ไม่ใช่เบอร์ทางการของธนาคาร — ห้ามกดหรือโทรตาม"
                ),
            },
            {
                "icon": "🏦",
                "title": "อ้างชื่อธนาคารหรือราชการ",
                "body": (
                    "\"ธนาคารกรุงเทพ\", \"กรมสรรพากร\", \"ตำรวจไซเบอร์\" "
                    "— หากสงสัย ให้โทรหาหน่วยงานนั้นโดยตรงด้วยเบอร์ที่รู้จัก ไม่ใช่เบอร์ในข้อความ"
                ),
            },
            {
                "icon": "😰",
                "title": "ข่มขู่หรือทำให้กลัว",
                "body": (
                    "\"คุณมีหมายศาล\", \"บัญชีถูกแฮก\", \"ต้องชำระเงินหรือจะถูกจับ\" "
                    "— มิจฉาชีพใช้ความกลัวทำให้คิดไม่ออก"
                ),
            },
        ],
        "tips_hotline_header": "### 📞 หมายเลขฉุกเฉิน",
        "tips_hotlines": [
            {"icon": "🆘", "label": "สายด่วนไซเบอร์", "number": "1599", "note": "ฟรี 24 ชั่วโมง"},
            {"icon": "🏦", "label": "ศูนย์แจ้งระงับธุรกรรม", "number": "1166", "note": "กรณีโอนเงินผิด"},
            {"icon": "👮", "label": "แจ้งความออนไลน์", "number": "1441", "note": "กองบัญชาการตำรวจสืบสวนฯ"},
        ],
        # ── Chatbot ───────────────────────────────────────────────────────
        "chat_quick_header": "#### คำถามยอดนิยม — กดเพื่อถามได้เลย",
        "chat_empty": "พิมพ์คำถามในช่องด้านล่าง หรือเลือกคำถามจากด้านบน",
        "chat_input_placeholder": "พิมพ์คำถามของท่านที่นี่...",
        "chat_clear_btn": "🗑️  ล้างการสนทนา",
        "chat_thinking": "กำลังคิดคำตอบ...",
        "chat_you": "คุณ",
        "chat_bot": "น้องการ์ด (ScamGuard AI)",
        "chat_err_empty": "⚠️ กรุณาพิมพ์คำถามก่อน",
        "chat_err_fail": "⏱️ ไม่สามารถเชื่อมต่อได้ในขณะนี้ กรุณาลองใหม่",
        "chat_hotline_remind": "📞 หากเป็นเรื่องด่วน โทรสายด่วนไซเบอร์ **1599** ได้เลย (ฟรี 24 ชม.)",
        # ── Feedback ──────────────────────────────────────────────────────
        "feedback_header": "**💬 ผลลัพธ์ไม่ถูกต้องหรือไม่? ช่วยบอกเราด้วยนะ**",
        "feedback_select_label": "เลือกคำตอบที่ถูกต้อง:",
        "feedback_placeholder": "-- กรุณาเลือก --",
        "feedback_options": ["", "ham (ข้อความปกติ)", "spam (สแปม)", "phishing (ฟิชชิ่ง)"],
        "btn_feedback": "📤 ส่งความคิดเห็น",
        "feedback_success": "✅ ขอบคุณ! เราจะนำข้อมูลนี้ไปปรับปรุงระบบให้ดียิ่งขึ้น",
        "feedback_fail": "⚠️ ไม่สามารถบันทึกได้ในขณะนี้ กรุณาลองใหม่",
        # ── Sidebar ───────────────────────────────────────────────────────
        "sidebar_header": "🛡️ ScamGuard",
        "sidebar_hotlines_header": "📞 สายด่วนฉุกเฉิน",
        "sidebar_hotlines": [
            {"number": "1599", "label": "สายด่วนไซเบอร์", "note": "ฟรี 24 ชั่วโมง"},
            {"number": "1166", "label": "ระงับธุรกรรม", "note": "กรณีโอนเงินผิด"},
            {"number": "1441", "label": "แจ้งความออนไลน์", "note": "ตำรวจสืบสวนฯ"},
        ],
        "sidebar_help_header": "❓ ต้องการความช่วยเหลือ?",
        "sidebar_help_body": (
            "**วิธีใช้งาน:**\n\n"
            "1. คัดลอกข้อความต้องสงสัย\n"
            "2. วางในช่องด้านขวา\n"
            "3. กด **ตรวจสอบความปลอดภัย**\n\n"
            "หากไม่แน่ใจ ให้ถามลูกหลานหรือ\n"
            "โทรสายด่วน **1599** ได้เลย"
        ),
        "sidebar_privacy_header": "🔒 นโยบายความเป็นส่วนตัว",
        "sidebar_privacy_body": (
            "ข้อความที่ท่านส่งมาตรวจสอบ **จะไม่ถูกเก็บ** "
            "หรือนำไปใช้เพื่อวัตถุประสงค์อื่น "
            "ระบบนี้ใช้เพื่อช่วยผู้สูงอายุป้องกันการถูกหลอกลวงเท่านั้น"
        ),
        # ── Footer ────────────────────────────────────────────────────────
        "footer": (
            "🛡️ <strong>ScamGuard</strong> v{ver} — ระบบตรวจสอบข้อความเพื่อผู้สูงอายุ<br>"
            "📞 สายด่วนไซเบอร์: <strong>1599</strong> &nbsp;|&nbsp; "
            "พัฒนาโดย DSBA Team"
        ).format(ver=APP_VERSION),
        "footer_privacy": (
            "🔒 ข้อความของท่านจะไม่ถูกเก็บหรือแชร์กับบุคคลที่สาม &nbsp;|&nbsp; "
            "❓ ต้องการความช่วยเหลือ กดที่ <strong>&gt;</strong> มุมซ้ายบนเพื่อเปิดเมนูช่วยเหลือ"
        ),
    },
    "en": {
        # ── Page ──────────────────────────────────────────────────────────
        "page_title": "ScamGuard — Email Safety Checker",
        "main_title": "🛡️ ScamGuard",
        "subtitle": "Email & Message Safety Checker — Protect yourself from online scams",
        # ── Tabs ──────────────────────────────────────────────────────────
        "tab_check": "🔍  Check a Message",
        "tab_tips": "📚  How to Spot Scams",
        "tab_chat": "💬  Ask AI",
        # ── 3-step guide ──────────────────────────────────────────────────
        "steps_header": "How it works — 3 simple steps",
        "step1_num": "1",
        "step1_icon": "📋",
        "step1_title": "Copy the suspicious message",
        "step1_body": (
            "Long-press the suspicious SMS, LINE, or email message "
            "and choose <strong>\"Copy\"</strong>."
        ),
        "step2_num": "2",
        "step2_icon": "📝",
        "step2_title": "Paste it in the box below",
        "step2_body": (
            "Long-press in the text box below and choose <strong>\"Paste\"</strong>, "
            "then press <strong>\"Check Message Safety\"</strong>."
        ),
        "step3_num": "3",
        "step3_icon": "🔍",
        "step3_title": "View your safety result",
        "step3_body": (
            "The result will appear instantly: "
            "<strong style='color:#2e7d32'>Safe</strong>, "
            "<strong style='color:#e65100'>Suspicious</strong>, or "
            "<strong style='color:#c62828'>Dangerous</strong>."
        ),
        # ── Input section ─────────────────────────────────────────────────
        "input_header": "### 📨 Paste the message you want to check here",
        "input_placeholder": (
            "Paste your message here...\n\n"
            "Example: \"You have won 50,000 Baht! Click this link to claim your prize.\""
        ),
        "examples_expander": "📋 View example messages for testing",
        "examples": {
            "⚠️ Spam — Prize": "ยินดีด้วยคุณได้รับรางวัล 100,000 บาท กดลิงก์เพื่อรับรางวัลก่อนหมดเวลา: bit.ly/reward-th",
            "🚨 Phishing — Bank": "แจ้งเตือนจากธนาคารกสิกรไทย บัญชีของท่านพบรายการผิดปกติ กรุณายืนยัน OTP: 456789 ภายใน 5 นาที",
            "🚨 Phishing — Police": "เจ้าหน้าที่ตำรวจไซเบอร์แจ้ง บัญชีของท่านเกี่ยวข้องกับคดีฟอกเงิน โทร 062-345-6789 ทันที",
            "✅ Safe message": "สวัสดีครับ วันนี้จะกลับบ้านช้าหน่อย รอหน่อยนะครับ",
        },
        "btn_analyze": "🔍  Check Message Safety",
        "btn_analyze_help": "Click to check whether this message is safe",
        "btn_clear": "🗑️  Clear",
        "spinner": "Checking your message, please wait...",
        "warn_empty": "⚠️ Please paste a message first before checking.",
        "err_timeout": "⏱️ The system is slow right now. Please try again.",
        "err_no_model": "❌ Model not found. Please contact support.",
        # ── Result section ────────────────────────────────────────────────
        "result_header": "### 📊 Safety Check Result",
        "result_safe_title": "✅  This message looks safe",
        "result_spam_title": "⚠️  This message is suspicious",
        "result_phishing_title": "🚨  This message is dangerous!",
        "result_safe_msg": (
            "No signs of scam or fraud were found in this message. "
            "Still, if you're not sure, ask a family member before clicking anything."
        ),
        "result_spam_msg": (
            "This message has suspicious signs — it may be unwanted advertising or spam. "
            "<strong>Do not click any links or call any numbers in this message.</strong>"
        ),
        "result_phishing_msg": (
            "This message may be trying to <strong>steal your personal information</strong> "
            "or <strong>trick you into sending money</strong>. "
            "Do NOT click any link, call any number, or give your password or OTP code."
        ),
        "result_reason_label": "Reason:",
        "result_keywords_label": "Warning words found:",
        "result_action_safe": "💡 Still unsure? Ask a trusted family member or friend.",
        "result_action_danger": (
            "🆘 If you have already been scammed, call the <strong>Cyber Hotline 1599</strong> immediately (free, 24/7)."
        ),
        # ── Education tips tab ────────────────────────────────────────────
        "tips_page_header": "## 📚 How to Spot Scam Emails & Messages",
        "tips_intro": (
            "Scammers often send messages pretending to be from banks, government agencies, "
            "or well-known companies to steal your information or money. "
            "Watch out for these warning signs:"
        ),
        "warning_signs": [
            {
                "icon": "⏰",
                "title": "Urgency & pressure",
                "body": (
                    "\"Urgent!\", \"Last day!\", \"Your account will be closed in 24 hours\" "
                    "— Scammers rush you so you act before you think."
                ),
            },
            {
                "icon": "🎁",
                "title": "Unexpected prizes or money",
                "body": (
                    "\"You have won 100,000 Baht!\" or \"You were selected as our lucky winner\" "
                    "— If you didn't enter a contest, you can't win one."
                ),
            },
            {
                "icon": "🔐",
                "title": "Asking for OTP or password",
                "body": (
                    "Real banks and government agencies <strong>will never ask for your OTP</strong> "
                    "or password over the phone or by message."
                ),
            },
            {
                "icon": "🔗",
                "title": "Strange links or phone numbers",
                "body": (
                    "Links with random letters and numbers like bit.ly/... or "
                    "phone numbers that don't match the official number — never click or call."
                ),
            },
            {
                "icon": "🏦",
                "title": "Claiming to be a bank or government",
                "body": (
                    "\"Bangkok Bank\", \"Revenue Department\", \"Cyber Police\" "
                    "— If in doubt, call the organization directly using a number you already know."
                ),
            },
            {
                "icon": "😰",
                "title": "Threats and fear tactics",
                "body": (
                    "\"You have a court summons\", \"Your account was hacked\", \"Pay now or be arrested\" "
                    "— Scammers use fear to stop you from thinking clearly."
                ),
            },
        ],
        "tips_hotline_header": "### 📞 Emergency Numbers",
        "tips_hotlines": [
            {"icon": "🆘", "label": "Cyber Crime Hotline", "number": "1599", "note": "Free, 24 hours"},
            {"icon": "🏦", "label": "Banking Fraud Center", "number": "1166", "note": "Wrong transfer"},
            {"icon": "👮", "label": "Online Crime Report", "number": "1441", "note": "DSI Online"},
        ],
        # ── Chatbot ───────────────────────────────────────────────────────
        "chat_quick_header": "#### Common Questions — tap to ask",
        "chat_empty": "Type your question in the box below, or choose a question above.",
        "chat_input_placeholder": "Type your question here...",
        "chat_clear_btn": "🗑️  Clear conversation",
        "chat_thinking": "Thinking of an answer...",
        "chat_you": "You",
        "chat_bot": "Guardian (ScamGuard AI)",
        "chat_err_empty": "⚠️ Please type a question first.",
        "chat_err_fail": "⏱️ Could not get a response right now. Please try again.",
        "chat_hotline_remind": "📞 For urgent matters, call the **Cyber Hotline: 1599** (free, 24/7)",
        # ── Feedback ──────────────────────────────────────────────────────
        "feedback_header": "**💬 Was the result incorrect? Please let us know.**",
        "feedback_select_label": "Select the correct answer:",
        "feedback_placeholder": "-- Please select --",
        "feedback_options": ["", "ham (Safe message)", "spam (Spam)", "phishing (Phishing)"],
        "btn_feedback": "📤 Submit Feedback",
        "feedback_success": "✅ Thank you! Your feedback helps improve the system.",
        "feedback_fail": "⚠️ Could not save feedback right now. Please try again.",
        # ── Sidebar ───────────────────────────────────────────────────────
        "sidebar_header": "🛡️ ScamGuard",
        "sidebar_hotlines_header": "📞 Emergency Hotlines",
        "sidebar_hotlines": [
            {"number": "1599", "label": "Cyber Crime Hotline", "note": "Free, 24 hours"},
            {"number": "1166", "label": "Block Transaction", "note": "Wrong transfer"},
            {"number": "1441", "label": "Report Online Crime", "note": "DSI Online"},
        ],
        "sidebar_help_header": "❓ Need Help?",
        "sidebar_help_body": (
            "**How to use:**\n\n"
            "1. Copy the suspicious message\n"
            "2. Paste it in the box on the right\n"
            "3. Press **Check Message Safety**\n\n"
            "If you're unsure, ask a family member\n"
            "or call hotline **1599** anytime."
        ),
        "sidebar_privacy_header": "🔒 Privacy Policy",
        "sidebar_privacy_body": (
            "The messages you submit **are not stored** "
            "or used for any other purpose. "
            "This system exists only to help senior citizens avoid online scams."
        ),
        # ── Footer ────────────────────────────────────────────────────────
        "footer": (
            "🛡️ <strong>ScamGuard</strong> v{ver} — Email Safety Checker for Seniors<br>"
            "📞 Cyber Hotline: <strong>1599</strong> &nbsp;|&nbsp; "
            "Built by DSBA Team"
        ).format(ver=APP_VERSION),
        "footer_privacy": (
            "🔒 Your messages are never stored or shared with any third party. &nbsp;|&nbsp; "
            "❓ Need help? Click <strong>&gt;</strong> in the top-left corner to open the help menu."
        ),
    },
}

# ---------------------------------------------------------------------------
# Page configuration (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ScamGuard — ตรวจสอบความปลอดภัย",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": f"ScamGuard v{APP_VERSION} — Email Safety Checker for Seniors",
    },
)

# ---------------------------------------------------------------------------
# Custom CSS — Elderly-Friendly Design
# Font: 20px base | Max-width: 860px | High contrast | Large buttons
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    /* ── Hide Streamlit chrome + sidebar entirely ── */
    [data-testid="stHeaderActionElements"] { display: none !important; }
    [data-testid="stToolbar"]              { display: none !important; }
    [data-testid="stDecoration"]           { display: none !important; }
    [data-testid="stStatusWidget"]         { display: none !important; }
    [data-testid="stSidebar"]              { display: none !important; }
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    [data-testid="collapsedControl"]       { display: none !important; }
    #MainMenu                              { display: none !important; }
    .stDeployButton                        { display: none !important; }


    /* ── Import Thai-friendly font ── */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap');

    /* ── Base typography — 20px minimum ── */
    html, body, [class*="css"] {
        font-family: 'Sarabun', 'Tahoma', 'Arial', sans-serif !important;
        font-size: 20px !important;
        line-height: 1.75 !important;
        color: #212121 !important;
    }

    /* ── Centered, readable container ── */
    .block-container {
        max-width: 860px !important;
        width: 94% !important;
        margin: 0 auto !important;
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* ── Page header ── */
    .page-header {
        text-align: center;
        padding: 1.2rem 0 0.5rem 0;
    }

    .page-title {
        font-size: 2.8rem !important;
        font-weight: 900 !important;
        color: #1a237e !important;
        margin: 0;
        line-height: 1.2;
    }

    .page-subtitle {
        font-size: 1.15rem !important;
        color: #455a64 !important;
        margin-top: 0.4rem;
    }

    /* ── Language toggle (top-right fixed) ── */
    .lang-toggle-wrap {
        position: fixed;
        top: 12px;
        right: 16px;
        z-index: 9999;
        background: rgba(255,255,255,0.95);
        border: 1.5px solid #c5cae9;
        border-radius: 20px;
        padding: 5px 14px;
        font-size: 1rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    .lang-active {
        color: #1a237e;
        font-weight: 800;
    }

    .lang-link {
        color: #78909c;
        text-decoration: none;
        font-weight: 600;
    }

    .lang-link:hover { color: #1a237e; }
    .lang-divider { color: #ccc; margin: 0 4px; }

    /* ── 3-step guide ── */
    .steps-wrap {
        background: #f0f4ff;
        border: 2px solid #3949ab;
        border-radius: 16px;
        padding: 1.4rem 1.6rem 1.2rem 1.6rem;
        margin: 1.2rem 0 1.6rem 0;
    }

    .steps-header {
        font-size: 1.4rem !important;
        font-weight: 900 !important;
        color: #1a237e;
        margin-bottom: 1rem;
        text-align: center;
    }

    .step-row {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        background: #ffffff;
        border: 2px solid #c5cae9;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 0.6rem 0;
    }

    .step-num {
        background: #1a237e;
        color: #ffffff;
        border-radius: 50%;
        min-width: 2.4rem;
        width: 2.4rem;
        height: 2.4rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        font-weight: 900;
        flex-shrink: 0;
    }

    .step-icon {
        font-size: 2rem;
        line-height: 1;
        flex-shrink: 0;
        margin-top: 0.1rem;
    }

    .step-content h4 {
        font-size: 1.15rem;
        font-weight: 800;
        color: #1a237e;
        margin: 0 0 0.3rem 0;
    }

    .step-content p {
        font-size: 1rem;
        color: #37474f;
        margin: 0;
        line-height: 1.7;
    }

    /* ── Input label ── */
    .stTextArea label,
    .stTextArea > label > div {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        color: #1a237e !important;
    }

    textarea {
        font-size: 1.15rem !important;
        line-height: 1.8 !important;
        border: 2px solid #9fa8da !important;
        border-radius: 10px !important;
    }

    textarea:focus {
        border-color: #3949ab !important;
        box-shadow: 0 0 0 3px rgba(57, 73, 171, 0.15) !important;
    }

    /* ── Primary button (Check Safety) ── */
    .stButton > button[kind="primary"] {
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        padding: 0.9rem 2rem !important;
        border-radius: 12px !important;
        width: 100% !important;
        background-color: #1a237e !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(26,35,126,0.3) !important;
        letter-spacing: 0.02em;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: #283593 !important;
        box-shadow: 0 6px 16px rgba(26,35,126,0.4) !important;
        transform: translateY(-1px);
    }

    /* ── Secondary button (Clear) ── */
    .stButton > button[kind="secondary"],
    .stButton > button:not([kind]) {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 10px !important;
        width: 100% !important;
        color: #37474f !important;
        border: 2px solid #b0bec5 !important;
    }

    /* ── Result cards ── */
    .result-card {
        border-radius: 16px;
        padding: 1.8rem 2rem;
        margin: 1.2rem 0;
        border: 3px solid;
    }

    .result-card-safe {
        background-color: #e8f5e9;
        border-color: #2e7d32;
    }

    .result-card-warn {
        background-color: #fff8e1;
        border-color: #f57f17;
    }

    .result-card-danger {
        background-color: #ffebee;
        border-color: #c62828;
    }

    .result-title {
        font-size: 2rem !important;
        font-weight: 900 !important;
        margin: 0 0 0.7rem 0;
        line-height: 1.3;
    }

    .result-title-safe    { color: #1b5e20; }
    .result-title-warn    { color: #bf360c; }
    .result-title-danger  { color: #b71c1c; }

    .result-body {
        font-size: 1.15rem !important;
        line-height: 1.85;
        color: #212121;
        margin: 0;
    }

    .result-keywords {
        margin-top: 1rem;
        font-size: 1rem !important;
        color: #424242;
    }

    .kw-tag {
        display: inline-block;
        background: #ffcdd2;
        color: #b71c1c;
        border-radius: 6px;
        padding: 2px 10px;
        margin: 2px 4px 2px 0;
        font-weight: 700;
        font-size: 0.95rem;
    }

    .kw-tag-safe {
        background: #c8e6c9;
        color: #1b5e20;
    }

    .result-action {
        margin-top: 1.2rem;
        font-size: 1.1rem !important;
        font-weight: 600;
        padding: 0.8rem 1.2rem;
        border-radius: 10px;
        background: rgba(0,0,0,0.04);
        border-left: 5px solid rgba(0,0,0,0.15);
    }

    /* ── Warning callout ── */
    .warn-callout {
        background: #fff3e0;
        border: 2px solid #ff6f00;
        border-radius: 12px;
        padding: 1rem 1.4rem;
        font-size: 1.1rem !important;
        font-weight: 600;
        color: #e65100;
        margin: 1rem 0;
    }

    /* ── Education tips ── */
    .tip-card {
        background: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin: 0.8rem 0;
        display: flex;
        align-items: flex-start;
        gap: 1rem;
    }

    .tip-icon {
        font-size: 2.2rem;
        flex-shrink: 0;
        line-height: 1;
        margin-top: 0.1rem;
    }

    .tip-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: #1a237e;
        margin: 0 0 0.3rem 0;
    }

    .tip-body {
        font-size: 1rem;
        color: #37474f;
        margin: 0;
        line-height: 1.7;
    }

    /* Hotline cards */
    .hotline-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin: 1rem 0;
    }

    .hotline-card {
        flex: 1 1 220px;
        background: #e3f2fd;
        border: 2px solid #1565c0;
        border-radius: 14px;
        padding: 1rem 1.3rem;
        text-align: center;
    }

    .hotline-number {
        font-size: 2.2rem !important;
        font-weight: 900 !important;
        color: #1565c0;
        line-height: 1.2;
    }

    .hotline-label {
        font-size: 1rem;
        font-weight: 700;
        color: #0d47a1;
        margin-top: 0.3rem;
    }

    .hotline-note {
        font-size: 1rem !important;
        color: #546e7a;
        margin-top: 0.2rem;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        padding: 0.7rem 1.4rem !important;
    }

    /* ── Streamlit alerts (warning/error/success) ── */
    .stAlert > div {
        font-size: 1.1rem !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        font-size: 1.1rem !important;
    }

    /* ── Chat UI ── */
    .chat-header {
        background: linear-gradient(135deg, #06C755 0%, #00A040 100%);
        color: white;
        border-radius: 16px;
        padding: 1rem 1.4rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 14px rgba(6, 199, 85, 0.3);
    }

    .chat-avatar {
        background: white;
        border-radius: 50%;
        width: 3rem;
        height: 3rem;
        min-width: 3rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
    }

    .chat-name {
        font-size: 1.2rem;
        font-weight: 900;
    }

    .chat-status {
        font-size: 1rem !important;
        opacity: 0.92;
    }

    .chat-badge {
        margin-left: auto;
        background: rgba(255,255,255,0.2);
        border-radius: 8px;
        padding: 0.2rem 0.7rem;
        font-size: 1rem !important;
        font-weight: 700;
    }

    /* Quick question pills */
    div[data-testid="stHorizontalBlock"] .stButton > button {
        border-radius: 20px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 0.4rem 0.9rem !important;
        background: white !important;
        color: #00A040 !important;
        border: 2px solid #06C755 !important;
    }

    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        background: #06C755 !important;
        color: white !important;
    }

    /* ── Footer ── */
    .page-footer {
        text-align: center;
        color: #607d8b;
        font-size: 1rem !important;
        padding: 1.5rem 0 0.5rem 0;
        line-height: 2;
    }

    /* ── Footer ── */
    .footer-privacy {
        text-align: center;
        font-size: 1rem !important;
        color: #78909c;
        padding: 0.5rem 0 1rem 0;
        line-height: 1.8;
    }

    /* ── tips intro text ── */
    .tips-intro {
        font-size: 1.1rem !important;
        color: #455a64;
        margin-bottom: 1rem;
        line-height: 1.8;
    }

    /* ── Mobile responsive ── */
    @media (max-width: 600px) {
        html, body, [class*="css"] { font-size: 18px !important; }
        .page-title   { font-size: 2.2rem !important; }
        .result-title { font-size: 1.7rem !important; }
        .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
        .lang-toggle-wrap { font-size: 1rem !important; padding: 4px 10px; }
        .hotline-card { flex: 1 1 100%; }
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []
if "total_checked" not in st.session_state:
    st.session_state.total_checked = 0
if "spam_found" not in st.session_state:
    st.session_state.spam_found = 0
if "lang" not in st.session_state:
    st.session_state.lang = "th"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_input_prefill" not in st.session_state:
    st.session_state.chat_input_prefill = ""
if "_chat_pending" not in st.session_state:
    st.session_state._chat_pending = None

# Read language from URL param
_qp = st.query_params
if "lang" in _qp and _qp["lang"] in ("th", "en"):
    st.session_state.lang = _qp["lang"]

T = TEXTS[st.session_state.lang]


# ---------------------------------------------------------------------------
# API helper functions
# ---------------------------------------------------------------------------
def call_predict_api(text: str, T: dict) -> dict | None:
    try:
        response = requests.post(
            f"{API_URL}/predict", json={"text": text}, timeout=10
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


def call_chat_api(message: str, history: list[dict], T: dict) -> str | None:
    payload = {"message": message, "history": history[-10:]}
    try:
        response = requests.post(f"{API_URL}/chat", json=payload, timeout=20)
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
    try:
        from src.api.chatbot import get_chatbot

        bot = get_chatbot()
        result = bot.chat(message=message, history=history)
        return result["reply"]
    except Exception as exc:
        return f"ขออภัย เกิดข้อผิดพลาด: {exc}"


def submit_feedback(text: str, predicted: str, actual: str) -> bool:
    try:
        response = requests.post(
            f"{API_URL}/feedback",
            json={"text": text, "predicted_label": predicted, "actual_label": actual},
            timeout=5,
        )
        return response.status_code == 200
    except Exception:
        return False


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "<br>")
    )


def _md_to_html(text: str) -> str:
    import re as _re

    text = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = _re.sub(r"\*([^*\n]+?)\*", r"<em>\1</em>", text)
    return text.replace("\n", "<br>")


# ---------------------------------------------------------------------------
# UI components
# ---------------------------------------------------------------------------

def render_steps(T: dict) -> None:
    """3-step how-to guide."""
    parts = [
        '<div class="steps-wrap">',
        f'<div class="steps-header">📖 {T["steps_header"]}</div>',
    ]
    for i in range(1, 4):
        num  = T[f"step{i}_num"]
        icon = T[f"step{i}_icon"]
        title = T[f"step{i}_title"]
        body  = T[f"step{i}_body"]
        parts.append(
            f'<div class="step-row">'
            f'<div class="step-num">{num}</div>'
            f'<div class="step-icon">{icon}</div>'
            f'<div class="step-content"><h4>{title}</h4><p>{body}</p></div>'
            f'</div>'
        )
    parts.append("</div>")
    st.markdown("\n".join(parts), unsafe_allow_html=True)


def display_result(result: dict, T: dict, original_text: str = "") -> None:
    """
    Elderly-friendly result card:
    - Big title with emoji
    - Plain-language explanation (no % confidence, no processing time)
    - Dangerous keywords shown as readable tags
    - Clear action advice
    """
    label = result.get("label", "ham")
    explanation = result.get("explanation", "")
    keywords = result.get("keywords", [])

    if label == "ham":
        card_cls   = "result-card result-card-safe"
        title_cls  = "result-title result-title-safe"
        title_txt  = T["result_safe_title"]
        body_txt   = T["result_safe_msg"]
        action_txt = T["result_action_safe"]
        kw_cls     = "kw-tag-safe"
    elif label == "spam":
        card_cls   = "result-card result-card-warn"
        title_cls  = "result-title result-title-warn"
        title_txt  = T["result_spam_title"]
        body_txt   = T["result_spam_msg"]
        action_txt = T["result_action_danger"]
        kw_cls     = "kw-tag"
    else:  # phishing
        card_cls   = "result-card result-card-danger"
        title_cls  = "result-title result-title-danger"
        title_txt  = T["result_phishing_title"]
        body_txt   = T["result_phishing_msg"]
        action_txt = T["result_action_danger"]
        kw_cls     = "kw-tag"

    # Keyword tags
    kw_html = ""
    if keywords:
        tags = "".join(f'<span class="{kw_cls}">{kw}</span>' for kw in keywords)
        kw_html = (
            f'<div class="result-keywords">'
            f'<strong>{T["result_keywords_label"]}</strong> {tags}'
            f'</div>'
        )

    # Explanation (from model) shown only when non-empty
    explanation_html = ""
    if explanation:
        explanation_html = (
            f'<p class="result-body" style="margin-top:0.6rem; font-style:italic; color:#546e7a;">'
            f'{T["result_reason_label"]} {explanation}'
            f'</p>'
        )

    st.markdown(
        f"""
        <div class="{card_cls}">
            <div class="{title_cls}">{title_txt}</div>
            <p class="result-body">{body_txt}</p>
            {explanation_html}
            {kw_html}
            <div class="result-action">{action_txt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Feedback section
    st.divider()
    st.markdown(T["feedback_header"])
    correct_label = st.selectbox(
        T["feedback_select_label"],
        options=T["feedback_options"],
        format_func=lambda x: T["feedback_placeholder"] if x == "" else x,
        key=f"feedback_select_{hash(original_text)}",
    )
    if correct_label:
        actual = correct_label.split(" ")[0]
        if st.button(T["btn_feedback"], key=f"feedback_btn_{hash(original_text)}"):
            if submit_feedback(original_text, label, actual):
                st.success(T["feedback_success"])
            else:
                st.warning(T["feedback_fail"])


def render_tips(T: dict) -> None:
    """Education section: warning signs + hotlines."""
    st.markdown(T["tips_page_header"])
    st.markdown(
        f'<p class="tips-intro">{T["tips_intro"]}</p>',
        unsafe_allow_html=True,
    )

    for sign in T["warning_signs"]:
        st.markdown(
            f'<div class="tip-card">'
            f'<div class="tip-icon">{sign["icon"]}</div>'
            f'<div>'
            f'<div class="tip-title">{sign["title"]}</div>'
            f'<div class="tip-body">{sign["body"]}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(T["tips_hotline_header"])
    hotline_cards = "".join(
        f'<div class="hotline-card">'
        f'<div style="font-size:1.6rem;">{h["icon"]}</div>'
        f'<div class="hotline-number">{h["number"]}</div>'
        f'<div class="hotline-label">{h["label"]}</div>'
        f'<div class="hotline-note">{h["note"]}</div>'
        f'</div>'
        for h in T["tips_hotlines"]
    )
    st.markdown(
        f'<div class="hotline-grid">{hotline_cards}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

# ── Language toggle (fixed top-right) ──────────────────────────────────────
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

# ── Logo / Header ───────────────────────────────────────────────────────────
_LOGO_PATH = Path(__file__).parent / "assets" / "scamguard_logo.png"

if _LOGO_PATH.exists():
    _lc, _mc, _rc = st.columns([1, 2, 1])
    with _mc:
        st.image(str(_LOGO_PATH), use_container_width=True)
else:
    st.markdown(
        f'<div class="page-header">'
        f'<div class="page-title">{T["main_title"]}</div>'
        f'<div class="page-subtitle">{T["subtitle"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div style="text-align:center; font-size:1.1rem; color:#546e7a; '
    f'padding-bottom:1rem;">{T["subtitle"]}</div>',
    unsafe_allow_html=True,
)

st.divider()

# ── Tabs ────────────────────────────────────────────────────────────────────
tab_check, tab_tips, tab_chat = st.tabs(
    [T["tab_check"], T["tab_tips"], T["tab_chat"]]
)

# ===========================================================================
# Tab 1: Check a Message
# ===========================================================================
with tab_check:
    # 3-step guide
    render_steps(T)

    st.divider()

    # Input
    st.markdown(T["input_header"])
    user_input = st.text_area(
        label="message_input",
        placeholder=T["input_placeholder"],
        height=180,
        label_visibility="collapsed",
        key="user_input_area",
    )

    # Quick test examples
    with st.expander(T["examples_expander"]):
        cols = st.columns(2)
        for i, (label, text) in enumerate(T["examples"].items()):
            with cols[i % 2]:
                st.markdown(f"**{label}**")
                st.code(text, language=None)

    # Buttons (full-width primary, then small secondary)
    analyze_clicked = st.button(
        T["btn_analyze"],
        type="primary",
        use_container_width=True,
        help=T["btn_analyze_help"],
    )
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
                st.divider()
                st.markdown(T["result_header"])
                display_result(result, T, original_text=user_input.strip())

                # Update counters
                st.session_state.total_checked += 1
                if result.get("label") != "ham":
                    st.session_state.spam_found += 1

                st.session_state.history.append(
                    {
                        "text": user_input.strip(),
                        "label": result.get("label"),
                        "label_th": result.get("label_th", ""),
                        "timestamp": datetime.now().strftime("%H:%M"),
                    }
                )

# ===========================================================================
# Tab 2: Education — How to Spot Scams
# ===========================================================================
with tab_tips:
    render_tips(T)

# ===========================================================================
# Tab 3: AI Chatbot
# ===========================================================================
with tab_chat:
    lang = st.session_state.lang
    online_txt = (
        "🟢 ออนไลน์ — ถามได้เลยครับ/ค่ะ" if lang == "th" else "🟢 Online — Ask me anything"
    )

    # Chat header
    st.markdown(
        f"""
        <div class="chat-header">
            <div class="chat-avatar">🛡️</div>
            <div>
                <div class="chat-name">{T["chat_bot"]}</div>
                <div class="chat-status">{online_txt}</div>
            </div>
            <div class="chat-badge">ScamGuard AI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick questions
    st.markdown(T["chat_quick_header"])
    quick_questions = CHAT_QUICK_QUESTIONS[lang]
    btn_cols = st.columns(3)
    for idx, q in enumerate(quick_questions):
        with btn_cols[idx % 3]:
            if st.button(q, key=f"quick_q_{idx}", use_container_width=True):
                st.session_state.chat_input_prefill = q

    st.divider()

    # Process prefill
    if st.session_state.chat_input_prefill:
        prefill = st.session_state.chat_input_prefill.strip()
        st.session_state.chat_input_prefill = ""
        st.session_state.chat_messages.append({"role": "user", "content": prefill})
        st.session_state._chat_pending = prefill
        st.rerun()

    # Empty state
    if not st.session_state.chat_messages and not st.session_state._chat_pending:
        st.info(T["chat_empty"])

    # Render messages
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(_escape_html(msg["content"]), unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="🛡️"):
                st.markdown(_md_to_html(msg["content"]), unsafe_allow_html=True)

    # Pending response
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

    # Clear button
    if st.session_state.chat_messages:
        if st.button(T["chat_clear_btn"], key="clear_chat_btn"):
            st.session_state.chat_messages = []
            st.rerun()

    # Chat input
    if prompt := st.chat_input(T["chat_input_placeholder"]):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        st.session_state._chat_pending = prompt
        st.rerun()

    st.info(T["chat_hotline_remind"])

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    f'<div class="page-footer">{T["footer"]}</div>',
    unsafe_allow_html=True,
)

# Help + Privacy expanders in footer
_fc1, _fc2 = st.columns(2)
with _fc1:
    with st.expander(T["sidebar_help_header"]):
        st.markdown(T["sidebar_help_body"])
with _fc2:
    with st.expander(T["sidebar_privacy_header"]):
        st.markdown(T["sidebar_privacy_body"])

st.markdown(
    f'<div class="footer-privacy">{T["footer_privacy"]}</div>',
    unsafe_allow_html=True,
)
