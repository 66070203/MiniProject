"""
Synthetic Thai SMS/LINE dataset generator for GuardianShield.

Generates realistic Thai-language spam, phishing, and ham messages
reflecting common patterns that affect elderly Thai users.
"""

import random
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.utils.config import get_config, get_project_root
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Message templates — Thai language
# ---------------------------------------------------------------------------

HAM_TEMPLATES = [
    # ── ข้อความครอบครัว / ชีวิตประจำวัน ──────────────────────────────────
    "สวัสดีครับ วันนี้อากาศดีมากเลยนะครับ",
    "แม่คะ วันนี้หนูจะกลับบ้านช้าหน่อย รอหน่อยนะคะ",
    "พรุ่งนี้นัดหมอที่โรงพยาบาล เวลา {time} นะครับ อย่าลืม",
    "คุณแม่ครับ ยาที่หมอสั่งกินหลังอาหารทุกมื้อนะครับ",
    "สวัสดีปีใหม่ครับ ขอให้มีสุขภาพแข็งแรง อายุยืนนะครับ",
    "คุณพ่อครับ วันอาทิตย์ครอบครัวจะไปทานข้าวด้วยกัน",
    "ร้านขายยาใกล้บ้านปิดปรับปรุงชั่วคราว กลับมาเปิดวันจันทร์",
    "นัดออกกำลังกายตอนเช้า เวลา {time} ที่สวนสาธารณะนะครับ",
    "ลูกฝากบอกว่าจะโทรมาคุยตอนเย็น รอรับสายด้วยนะครับ",
    "ขอบคุณที่ดูแลหลานนะครับ เดี๋ยวจะไปรับตอน {time}",
    "วันนี้อาหารกลางวันทำอะไรดีครับ หิวแล้ว",
    "อย่าลืมกินยาความดันนะครับ ทุกเช้า",
    "โทรหาหน่อยนะครับ มีเรื่องจะคุย",
    "ไฟฟ้าจะดับในหมู่บ้านพรุ่งนี้ช่วง {time} ถึง {time2}",
    "สมัครสมาชิกห้องสมุดได้แล้ว ฟรีทุกกิจกรรม",
    "วันนี้ฝนตก ระวังลื่นนะครับ",
    "ขอให้หายป่วยเร็วๆ นะครับ",
    "เพื่อนบ้านฝากบอกว่า พรุ่งนี้จะเอาผักมาให้",
    "วัดจะมีงานทำบุญวันที่ {date} นะครับ",
    "ไม่ต้องห่วงนะครับ ทุกอย่างเป็นปกติดี",
    "ครอบครัวส่งความระลึกถึงมาด้วยนะครับ",
    "หลานฝากบอกว่ารักคุณตายายมากนะครับ",
    "ร้านอาหารใกล้บ้านเปิดใหม่ รสชาติดีมาก",
    "ช่วยซื้อของจากตลาดมาให้หน่อยได้ไหมครับ",
    "วันเกิดลูกสาวแล้ว อย่าลืมโทรไปอวยพรนะ",
    # ── แจ้งเตือนจากธนาคารจริง (ไม่มีลิงก์/OTP/การขอข้อมูล) ────────────
    "แจ้งเตือนจากธนาคาร{bank} กรุณาติดต่อได้ที่ธนาคาร{bank}ทุกสาขา",
    "ธนาคาร{bank} แจ้งว่าสาขาใกล้บ้านท่านเปิดให้บริการ จันทร์–ศุกร์ {time}–{time2} น.",
    "ธนาคาร{bank}: บัตร ATM ของท่านหมดอายุในเดือนหน้า กรุณาติดต่อสาขาเพื่อต่ออายุบัตร",
    "ธนาคาร{bank} ขอแจ้งว่าระบบจะปิดปรับปรุงชั่วคราว คืนนี้ {time}–{time2} น.",
    "แจ้งเตือน: บัญชีออมทรัพย์ธนาคาร{bank} ของท่านได้รับดอกเบี้ยประจำเดือนแล้ว",
    "ธนาคาร{bank} ขอแจ้งอัตราดอกเบี้ยเงินฝากใหม่ มีผลตั้งแต่วันที่ {date} สอบถามได้ที่สาขา",
    "ธนาคาร{bank}: ท่านสามารถตรวจสอบยอดบัญชีผ่านแอปพลิเคชันธนาคารได้ตลอด 24 ชั่วโมง",
    "แจ้งจากธนาคาร{bank}: สาขา {location} เปิดให้บริการตามปกติแล้ว",
    "ธนาคาร{bank} ขอขอบคุณที่ใช้บริการ หากมีข้อสงสัยติดต่อได้ที่สาขาหรือ Call Center",
    "ธนาคาร{bank}: โปรดตรวจสอบรายการเคลื่อนไหวบัญชีผ่านแอปหรือตู้ ATM ของธนาคาร",
    # ── แจ้งเตือนจากหน่วยงานราชการ/สาธารณูปโภคจริง ────────────────────
    "การไฟฟ้าฯ แจ้งว่าจะดำเนินการตัดต้นไม้ใกล้สายไฟในหมู่บ้าน วันที่ {date}",
    "ประกันสังคมแจ้ง: ท่านสามารถตรวจสอบสิทธิ์ได้ที่สำนักงานประกันสังคมทุกจังหวัด",
    "กรมสรรพากรแจ้ง: กำหนดการยื่นภาษีเงินได้บุคคลธรรมดาปีนี้ สิ้นสุดวันที่ {date}",
    "โรงพยาบาล{location} แจ้งนัดผู้ป่วยประจำ วันที่ {date} เวลา {time} น. กรุณามาตามนัด",
    "เทศบาลแจ้ง: งดจ่ายน้ำประปาชั่วคราว วันที่ {date} เวลา {time}–{time2} น. เพื่อซ่อมท่อ",
    "สำนักงานเขตแจ้ง: โครงการฉีดวัคซีนผู้สูงอายุฟรี วันที่ {date} ที่ศูนย์บริการสาธารณสุข",
    "อบต.แจ้ง: การประชุมประชาคมหมู่บ้านวันที่ {date} เวลา {time} น. ณ ศาลาประชาคม",
    # ── แจ้งเตือนจาก True/AIS/DTAC จริง (ไม่มีลิงก์หลอกลวง) ─────────
    "AIS แจ้ง: แพ็กเกจโทรศัพท์ของท่านจะหมดอายุวันที่ {date} กรุณาต่ออายุที่ศูนย์บริการ AIS",
    "True Move H แจ้ง: ท่านใช้อินเทอร์เน็ตครบโควต้าแล้ว ความเร็วจะลดลงจนกว่าจะถึงรอบบิลใหม่",
    "DTAC แจ้ง: ยอดค่าโทรเดือนนี้ของท่านคือ {course_price} บาท กำหนดชำระภายในวันที่ {date}",
    # ── ประกาศจากสถาบันการศึกษา / อบรม / สัมมนา ─────────────────────
    "ศูนย์ภาษา {university} เปิดรับสมัครคอร์ส {course_name} รุ่นที่ {batch} วันที่ {date}–{date2} ค่าลงทะเบียน {course_price} บาท สมัคร: {legit_url}",
    "คณะวิศวกรรมศาสตร์ {university} ขอเชิญเข้าร่วมสัมมนา {course_name} วันที่ {date} ไม่เสียค่าใช้จ่าย ลงทะเบียน: {legit_url}",
    "มหาวิทยาลัย{university} ประกาศรับสมัครอบรม {course_name} ประจำปี {year} รับจำนวนจำกัด {seats} ที่นั่ง สมัคร: {legit_url}",
    "โครงการอบรมวิชาชีพ {course_name} เรียนออนไลน์ผ่าน MS Teams วันที่ {date} เวลา 09.00–16.00 น. ค่าลงทะเบียน {course_price} บาท",
    "ประกาศจากฝ่ายทรัพยากรบุคคล: เปิดรับสมัครอบรม {course_name} ประจำปี {year} นักศึกษา/บุคลากร ค่าลงทะเบียน {course_price} บาท รายละเอียด: {legit_url}",
    "สมาคมวิชาชีพ{university} ขอเชิญเข้าร่วมประชุมวิชาการ วันที่ {date} ณ อาคาร{location} ค่าลงทะเบียน {course_price} บาท สมัคร: {legit_url}",
    "แจ้งตารางสอบ {course_name} ประจำปี {year} สำหรับนักศึกษา ตรวจสอบตารางและสมัครสอบได้ที่ {legit_url}",
    "กองทุนการศึกษา แจ้ง: เปิดรับสมัครทุน{course_name} ประจำปี {year} กรอกใบสมัครออนไลน์ที่ {legit_url} ก่อนวันที่ {date}",
    "ศูนย์บริการวิชาการ {university} เปิดคอร์ส {course_name} Fast Track รุ่นใหม่ เน้นทำข้อสอบจริง {course_price} บาท โทรสอบถาม: {phone_real}",
    "ประกาศ {university}: การอบรม {course_name} สำหรับนักศึกษาและศิษย์เก่า ราคาพิเศษ {course_price} บาท บุคคลทั่วไป {course_price2} บาท สมัครได้ถึงวันที่ {date}: {legit_url}",
    # ── โปรโมชั่นธุรกิจที่ถูกกฎหมาย (มีลิงก์ legit) ─────────────────
    "ร้าน{location} ฉลองครบรอบ {years} ปี ลด {discount}% ทุกเมนู วันที่ {date}–{date2} จองโต๊ะล่วงหน้า: {legit_url}",
    "คลินิก{location} แจ้ง: โปรแพ็กเกจตรวจสุขภาพประจำปี ราคา {course_price} บาท นัดหมายออนไลน์: {legit_url}",
    "โรงแรม{location} โปรโมชั่นพักผ่อนช่วงหยุดยาว ราคาเริ่มต้น {course_price} บาท/คืน จองได้ที่ {legit_url}",
    "ประกันสุขภาพ{university} โปรพิเศษสำหรับผู้สูงอายุ เบี้ยประกันเริ่ม {course_price} บาท/ปี ข้อมูลเพิ่มเติม: {legit_url}",
]

SPAM_TEMPLATES = [
    "ยินดีด้วย! คุณได้รับรางวัลใหญ่ {prize} บาท กดลิงก์เพื่อรับรางวัล: {url}",
    "🎉 โปรโมชั่นพิเศษ! ลดราคา {discount}% ทุกสินค้า วันนี้วันเดียว กด: {url}",
    "คุณถูกเลือกรับเงิน {prize} บาทจากโครงการพิเศษ โทร {phone} ด่วน!",
    "สมัครสินเชื่อด่วน อนุมัติทันที ไม่ต้องมีหลักทรัพย์ โทร {phone}",
    "รับฟรี! ของขวัญมูลค่า {prize} บาท เพียงกรอกข้อมูล: {url}",
    "แจ้งเตือน: บัญชีของคุณมีปัญหา กดที่นี่เพื่อแก้ไข: {url} ด่วน!",
    "เงินกู้ด่วน อนุมัติภายใน {time} นาที ดอกเบี้ยต่ำ โทร {phone}",
    "ลงทุนกับเราวันนี้ กำไร {profit}% ต่อเดือน ไม่มีความเสี่ยง: {url}",
    "ขอแสดงความยินดี! คุณชนะการจับฉลาก รางวัล {prize} บาท ยืนยัน: {url}",
    "โปรแกรมพิเศษสำหรับผู้สูงอายุ รับเงิน {prize} บาทต่อเดือน โทร {phone}",
    "Flash Sale! {discount}% OFF เฉพาะ {time} ชั่วโมง สั่งได้ที่: {url}",
    "คุณมีสิทธิ์รับประกันสังคมพิเศษ {prize} บาท ลงทะเบียน: {url}",
    "ร้านใหม่เปิด! ซื้อ 1 แถม 1 ทุกเมนู วันนี้เท่านั้น กด: {url}",
    "ชนะรางวัล iPhone ใหม่ล่าสุด! รีบยืนยันก่อนหมดเวลา: {url}",
    "โปรพิเศษ! เติมเงิน {prize} บาท ได้รับ {bonus} บาท โทร {phone}",
    "ด่วน! บัตรของคุณถูกระงับ ติดต่อเราที่ {phone} หรือ {url}",
    "ฟรี! ทริปท่องเที่ยว {place} {nights} คืน เพียงกรอกแบบสอบถาม: {url}",
    "สมัครวันนี้รับ {prize} บาททันที โปรนี้มีจำนวนจำกัด: {url}",
]

PHISHING_TEMPLATES = [
    "แจ้งเตือนจาก {bank}: บัญชีของท่านพบรายการผิดปกติ กรุณายืนยัน OTP: {otp} ภายใน {time} นาที",
    "ธนาคาร{bank}แจ้ง: รหัส OTP ของท่านคือ {otp} ห้ามบอกใครเด็ดขาด รวมถึงพนักงานธนาคาร",
    "เจ้าหน้าที่ธนาคาร: บัตรของท่านจะถูกระงับ กรุณาโทรยืนยัน {phone} ด่วน",
    "LINE แจ้งเตือน: มีคนพยายามเข้าสู่ระบบบัญชีของคุณ กรุณายืนยัน: {url}",
    "กสทช.แจ้ง: เบอร์ {phone_short} ของท่านจะถูกระงับ กรุณายืนยันที่ {url}",
    "กรมสรรพากรแจ้ง: ท่านมีเงินคืนภาษี {prize} บาท กรอกข้อมูลรับเงิน: {url}",
    "ตำรวจไซเบอร์แจ้ง: บัญชีของท่านเกี่ยวข้องกับคดีฟอกเงิน โทร {phone} ทันที",
    "เจ้าหน้าที่ประกันสังคมแจ้ง: ท่านมีสิทธิ์รับเงิน {prize} บาท ยืนยัน: {url}",
    "True Money: บัญชีของท่านจะถูกปิด กรุณากรอก OTP {otp} เพื่อยืนยัน",
    "ธนาคาร{bank}: พบการใช้บัตรผิดปกติที่ {location} โทรยืนยัน {phone} ทันที",
    "iCloud แจ้ง: Apple ID ของคุณถูกล็อก กรุณายืนยันผ่าน: {url}",
    "Facebook แจ้ง: บัญชีของคุณอาจถูกแฮก ยืนยันตัวตนที่: {url} ภายใน {time} นาที",
    "ส่งพัสดุไม่ได้ เนื่องจากที่อยู่ไม่ครบ กรุณายืนยัน: {url} มิฉะนั้นพัสดุจะถูกส่งคืน",
    "แจ้งเตือน! พบไวรัสในโทรศัพท์ กดทันทีเพื่อลบ: {url} ก่อนข้อมูลสูญหาย",
    "เจ้าหน้าที่กรุงเทพมหานคร: ท่านค้างค่าปรับ {prize} บาท ชำระที่ {url} หรือโทร {phone}",
    "โปรดยืนยัน: รหัส OTP {otp} ใช้สำหรับการทำธุรกรรม {prize} บาท ที่ธนาคาร{bank}",
    "ด่วนมาก! บัตร ATM ของท่านจะหมดอายุพรุ่งนี้ ต่ออายุออนไลน์: {url}",
    "เจ้าหน้าที่ศาล: ท่านมีหมายเรียก กรุณาติดต่อ {phone} ภายใน {time} ชั่วโมง",
]

# Filler data for template variables
PRIZES = [5000, 10000, 20000, 50000, 100000, 500000, 1000000]
DISCOUNTS = [30, 50, 70, 80, 90]
PROFITS = [20, 30, 50, 100, 200]
BANKS = ["กสิกรไทย", "กรุงไทย", "ไทยพาณิชย์", "กรุงเทพ", "ทหารไทยธนชาต"]
LOCATIONS = ["เชียงใหม่", "ภูเก็ต", "สุราษฎร์ธานี", "ต่างประเทศ", "ออนไลน์"]
PLACES = ["ญี่ปุ่น", "เกาหลี", "ยุโรป", "ออสเตรเลีย", "สิงคโปร์"]
TIMES = ["08:00", "09:00", "10:00", "13:00", "14:00", "15:00", "16:00"]

FAKE_URLS = [
    "bit.ly/reward-th",
    "tinyurl.com/claim-now",
    "gg.gg/thai-prize",
    "thai-bank-verify.net/login",
    "krungsri-secure.cc/confirm",
    "scb-auth.xyz/verify",
    "line-verify.net/account",
    "tmb-secure.info/otp",
]

# Legitimate URLs used in ham templates (educational/institutional/business)
LEGIT_URLS = [
    "forms.gle/xXec3Zjw76FdeNkKA",
    "forms.gle/abc123def456",
    "docs.google.com/forms/d/e/example",
    "language.kmitl.ac.th",
    "reg.kmutt.ac.th/register",
    "training.chula.ac.th/course",
    "cpe.ku.ac.th/event",
    "human.mfu.ac.th/training",
    "shortcourse.nida.ac.th",
    "elearning.mhesi.go.th",
    "personnel.moph.go.th/training",
    "skillplus.dsd.go.th",
]

UNIVERSITIES = ["สจล.", "จุฬาฯ", "ธรรมศาสตร์", "มหิดล", "เกษตรศาสตร์", "บูรพา", "นเรศวร", "KMUTT", "NIDA", "KMITL"]
COURSE_NAMES = ["TOEIC Fast Track", "Excel ขั้นสูง", "Python สำหรับนักธุรกิจ", "การบริหารโครงการ PMP", "ภาษาอังกฤษเพื่อธุรกิจ", "Data Analytics", "AI สำหรับผู้เริ่มต้น", "การเงินส่วนบุคคล"]
COURSE_PRICES = [499, 699, 799, 999, 1200, 1500, 1800, 2000, 2500, 3000]
REAL_PHONES = ["02-329-8000", "02-470-8000", "02-218-0000", "02-564-4440", "053-916-100"]

FAKE_PHONES = [
    "062-345-6789",
    "081-234-5678",
    "095-678-9012",
    "02-123-4567",
    "1234",
    "1800-xxx-xxx",
]

FAKE_OTPS = [
    "123456",
    "987654",
    "456789",
    "234567",
    "876543",
]


def _random_template_vars() -> dict:
    """Generate random filler values for template placeholders."""
    price = random.choice(COURSE_PRICES)
    return {
        "prize": f"{random.choice(PRIZES):,}",
        "discount": random.choice(DISCOUNTS),
        "profit": random.choice(PROFITS),
        "bank": random.choice(BANKS),
        "location": random.choice(LOCATIONS),
        "place": random.choice(PLACES),
        "url": random.choice(FAKE_URLS),
        "phone": random.choice(FAKE_PHONES),
        "phone_short": f"0{random.randint(80, 99)}-xxx-{random.randint(1000, 9999)}",
        "otp": random.choice(FAKE_OTPS),
        "time": random.choice(TIMES),
        "time2": random.choice(TIMES),
        "nights": random.randint(3, 7),
        "bonus": f"{random.choice(PRIZES) * 2:,}",
        "date": f"{random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(67, 68)}",
        # Ham-specific variables for educational/institutional messages
        "legit_url": random.choice(LEGIT_URLS),
        "university": random.choice(UNIVERSITIES),
        "course_name": random.choice(COURSE_NAMES),
        "course_price": price,
        "course_price2": price + random.choice([200, 300, 500]),
        "batch": random.randint(1, 20),
        "seats": random.choice([20, 30, 40, 50, 60]),
        "year": random.choice([2568, 2569]),
        "years": random.randint(5, 30),
        "date2": f"{random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(67, 68)}",
        "phone_real": random.choice(REAL_PHONES),
    }


def _fill_template(template: str) -> str:
    """Substitute placeholders in a message template."""
    vars_ = _random_template_vars()
    try:
        return template.format(**vars_)
    except KeyError:
        return template  # Return as-is if extra placeholders


def _add_noise(text: str) -> str:
    """Randomly add minor text variations to increase diversity."""
    suffixes = ["", " ค่ะ", " ครับ", " นะ", " นะคะ", " นะครับ", " จ้า", ""]
    prefixes = ["", "📢 ", "⚠️ ", "🔔 ", "‼️ ", ""]
    if random.random() < 0.3:
        text = random.choice(prefixes) + text
    if random.random() < 0.2:
        text = text + random.choice(suffixes)
    return text.strip()


def generate_dataset(
    n_ham: int = 2500,
    n_spam: int = 2000,
    n_phishing: int = 1500,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Generate a synthetic Thai spam/phishing/ham dataset.

    Args:
        n_ham: Number of legitimate messages
        n_spam: Number of spam messages
        n_phishing: Number of phishing messages
        random_state: Random seed for reproducibility

    Returns:
        DataFrame with columns [message_id, text, label, source, created_at]
    """
    random.seed(random_state)
    logger.info(
        f"Generating synthetic dataset: ham={n_ham}, spam={n_spam}, phishing={n_phishing}"
    )

    records = []
    start_date = datetime(2023, 1, 1)

    def _random_date() -> str:
        delta = timedelta(days=random.randint(0, 730))
        return (start_date + delta).strftime("%Y-%m-%d %H:%M:%S")

    def _make_records(templates: list[str], label: int, n: int) -> list[dict]:
        rows = []
        for _ in range(n):
            template = random.choice(templates)
            text = _add_noise(_fill_template(template))
            rows.append(
                {
                    "message_id": str(uuid.UUID(int=random.getrandbits(128))),
                    "text": text,
                    "label": label,
                    "label_name": ["ham", "spam", "phishing"][label],
                    "source": "synthetic",
                    "created_at": _random_date(),
                }
            )
        return rows

    records.extend(_make_records(HAM_TEMPLATES, 0, n_ham))
    records.extend(_make_records(SPAM_TEMPLATES, 1, n_spam))
    records.extend(_make_records(PHISHING_TEMPLATES, 2, n_phishing))

    df = pd.DataFrame(records)
    df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)

    logger.info(
        f"Generated {len(df)} records. Label distribution:\n{df['label_name'].value_counts().to_string()}"
    )
    return df


def save_synthetic_dataset(output_path: str | None = None) -> str:
    """
    Generate and save the synthetic dataset to CSV.

    Args:
        output_path: Optional custom output path. Defaults to config setting.

    Returns:
        Absolute path to saved CSV file
    """
    config = get_config()
    root = get_project_root()

    if output_path is None:
        output_path = (
            root / config["paths"]["data_raw"] / config["data"]["synthetic_file"]
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_dataset(
        n_ham=config["synthetic"]["n_ham"],
        n_spam=config["synthetic"]["n_spam"],
        n_phishing=config["synthetic"]["n_phishing"],
        random_state=config["data"]["random_state"],
    )
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"Synthetic dataset saved to: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    path = save_synthetic_dataset()
    print(f"Dataset saved to: {path}")
