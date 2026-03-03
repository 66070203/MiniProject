"""
Pytest shared fixtures for GuardianShield tests.
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Ensure project root is in path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Override config path for tests
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session")
def sample_df() -> pd.DataFrame:
    """Small sample DataFrame representing the full dataset schema."""
    return pd.DataFrame(
        [
            {
                "message_id": "aaa-111",
                "text": "สวัสดีครับ วันนี้หนูจะกลับบ้านช้าหน่อย รอหน่อยนะครับ",
                "label": 0,
                "label_name": "ham",
                "source": "synthetic",
                "created_at": "2024-01-01 10:00:00",
            },
            {
                "message_id": "bbb-222",
                "text": "ยินดีด้วย! คุณได้รับรางวัล 50,000 บาท กดลิงก์เพื่อรับรางวัล: bit.ly/reward",
                "label": 1,
                "label_name": "spam",
                "source": "synthetic",
                "created_at": "2024-01-02 11:00:00",
            },
            {
                "message_id": "ccc-333",
                "text": "แจ้งเตือนจากธนาคารกสิกรไทย บัญชีพบรายการผิดปกติ ยืนยัน OTP: 123456 ภายใน 5 นาที",
                "label": 2,
                "label_name": "phishing",
                "source": "synthetic",
                "created_at": "2024-01-03 12:00:00",
            },
            {
                "message_id": "ddd-444",
                "text": "อย่าลืมกินยาความดันทุกเช้านะครับ หมอสั่งไว้",
                "label": 0,
                "label_name": "ham",
                "source": "synthetic",
                "created_at": "2024-01-04 08:00:00",
            },
            {
                "message_id": "eee-555",
                "text": "โปรโมชั่นพิเศษ! ลดราคา 80% ทุกสินค้า วันนี้วันเดียว กด: tinyurl.com/deal",
                "label": 1,
                "label_name": "spam",
                "source": "synthetic",
                "created_at": "2024-01-05 14:00:00",
            },
            {
                "message_id": "fff-666",
                "text": "เจ้าหน้าที่ตำรวจไซเบอร์แจ้ง บัญชีของท่านเกี่ยวข้องกับคดีฟอกเงิน โทร 062-345-6789",
                "label": 2,
                "label_name": "phishing",
                "source": "synthetic",
                "created_at": "2024-01-06 09:00:00",
            },
        ]
    )


@pytest.fixture(scope="session")
def spam_texts() -> list[str]:
    return [
        "ยินดีด้วยคุณได้รับรางวัล 100,000 บาท กดลิงก์เพื่อรับ: bit.ly/win",
        "โปรโมชั่นพิเศษ ลด 90% วันนี้เท่านั้น สั่งได้เลย",
        "สมัครสินเชื่อด่วน อนุมัติทันที โทร 081-234-5678",
    ]


@pytest.fixture(scope="session")
def phishing_texts() -> list[str]:
    return [
        "แจ้งเตือนจากธนาคาร OTP ของท่านคือ 456789 ห้ามบอกใคร",
        "บัญชีจะถูกระงับ กรุณายืนยันที่ thai-bank-verify.net/login",
        "ตำรวจไซเบอร์แจ้ง เกี่ยวข้องคดีฟอกเงิน โทร 095-678-9012 ทันที",
    ]


@pytest.fixture(scope="session")
def ham_texts() -> list[str]:
    return [
        "สวัสดีครับ วันนี้หนูจะกลับบ้านช้าหน่อย",
        "อย่าลืมกินยาความดันนะครับ ทุกเช้า",
        "พรุ่งนี้นัดหมอ เวลา 09:00 อย่าลืมนะครับ",
    ]


@pytest.fixture(scope="function")
def temp_dir(tmp_path) -> Path:
    """Provide a temporary directory for each test."""
    return tmp_path


@pytest.fixture(scope="session")
def preprocessor():
    """Shared ThaiTextPreprocessor instance."""
    from src.data.preprocessor import ThaiTextPreprocessor

    return ThaiTextPreprocessor(remove_stopwords=False, engine="newmm")
