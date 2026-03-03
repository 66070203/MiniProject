# GuardianShield (ผู้พิทักษ์)

ระบบ AI ตรวจจับข้อความสแปมและฟิชชิ่งสำหรับผู้สูงอายุ

---

## สิ่งที่ต้องเตรียม

- Python 3.11+
- Docker Desktop (สำหรับรันแบบ container)
- Groq API Key — สมัครฟรีได้ที่ [console.groq.com](https://console.groq.com)

---

## วิธีรันด้วย Docker (แนะนำ)

### 1. ติดตั้ง dependencies และเทรนโมเดล

```bash
pip install -r requirements.txt

python -m src.data.generator      # สร้างชุดข้อมูล
python -m src.data.ingestion      # แบ่ง train/val/test
python -m src.models.trainer      # เทรนโมเดล (~2-3 นาที)
```

### 2. ตั้งค่า API Key

สร้างไฟล์ `.env` ในโฟลเดอร์ `guardianshield/`:

```
GROQ_API_KEY=ใส่ key ที่ได้จาก console.groq.com ตรงนี้
```

### 3. รัน Docker

```bash
docker compose up -d
```

### 4. เปิดใช้งาน

| บริการ | URL |
|--------|-----|
| หน้าเว็บ (Streamlit) | http://localhost:8501 |
| API | http://localhost:8000/docs |
| MLflow | http://localhost:5001 |

---

## วิธีรันแบบ Local (ไม่ใช้ Docker)

เปิด terminal 3 หน้าต่าง:

**Terminal 1 — API:**
```bash
set GROQ_API_KEY=ใส่ key ที่นี่
uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 — หน้าเว็บ:**
```bash
streamlit run app/streamlit_app.py
```

**Terminal 3 — MLflow:**
```bash
mlflow server --backend-store-uri mlruns --host 0.0.0.0 --port 5001
```

---

## วิธีใช้ API

ส่ง POST request ไปที่ `/predict`:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "ยินดีด้วย! คุณได้รับรางวัล 100,000 บาท กดลิงก์เพื่อรับ: bit.ly/claim"}'
```

ผลลัพธ์:

```json
{
  "label": "spam",
  "label_th": "สแปม",
  "confidence": 0.99,
  "risk_level": "high",
  "explanation": "พบคำเสี่ยง: รางวัล, กด | พบลิงก์ URL",
  "confidence_source": "ml",
  "llm_explanation": null
}
```

เมื่อโมเดล ML ไม่มั่นใจ (confidence < 80%) ระบบจะเรียก Groq LLM โดยอัตโนมัติ:

```json
{
  "label": "ham",
  "confidence": 0.87,
  "confidence_source": "hybrid",
  "llm_explanation": "ข้อความแจ้งเตือนดอกเบี้ยจากธนาคาร ไม่มีการขอข้อมูลส่วนตัวหรือลิงก์น่าสงสัย"
}
```

---

## เทรนโมเดลใหม่

```bash
python -m src.data.generator    # สร้างข้อมูลใหม่
python -m src.data.ingestion    # แบ่งชุดข้อมูล
python -m src.models.trainer    # เทรน + บันทึกผลใน MLflow

# หลังเทรนเสร็จ restart API เพื่อโหลดโมเดลใหม่
docker compose restart api
```

---

## รัน Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --cov=src --cov-report=term-missing
```
