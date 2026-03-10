# ScamGuard (สแกมการ์ด)
ระบบ AI ตรวจจับข้อความสแปมและฟิชชิ่งสำหรับผู้สูงอายุ

---

## สิ่งที่ต้องเตรียม

- Python 3.11+
- Docker Desktop (สำหรับรันแบบ container)
- Groq API Key — สมัครฟรีได้ที่ [console.groq.com](https://console.groq.com)
- LINE Messaging API Channel — สร้างได้ที่ [developers.line.biz](https://developers.line.biz) (ถ้าต้องการใช้ LINE Bot)

---

## วิธีรันด้วย Docker (แนะนำ)

### 1. ติดตั้ง dependencies และเทรนโมเดล

```bash
pip install -r requirements.txt

python -m src.data.generator      # สร้างชุดข้อมูล
python -m src.data.ingestion      # แบ่ง train/val/test
python -m src.models.trainer      # เทรนโมเดล (~2-3 นาที)
```

### 2. ตั้งค่า API Keys

สร้างไฟล์ `.env` (copy จาก `.env.example`):

```bash
cp .env.example .env
```

แก้ไขค่าใน `.env`:

```
GROQ_API_KEY=ใส่ key ที่ได้จาก console.groq.com ตรงนี้

# LINE Bot (ไม่บังคับ — ข้ามได้ถ้าไม่ใช้)
LINE_CHANNEL_SECRET=ใส่ channel secret ตรงนี้
LINE_CHANNEL_ACCESS_TOKEN=ใส่ channel access token ตรงนี้
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
| MLflow | http://localhost:5000 |

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

## ตั้งค่า LINE Bot (ไม่บังคับ)

ScamGuard รองรับ LINE Messaging API — ผู้ใช้ส่งข้อความมาที่บอทแล้วได้รับผลวิเคราะห์กลับเป็นภาษาไทยทันที

### 1. สร้าง LINE Messaging API Channel

1. ไปที่ [developers.line.biz](https://developers.line.biz) → **Console**
2. สร้าง Provider → สร้าง Channel ประเภท **Messaging API**
3. เข้าไปที่ Channel → **Messaging API** tab
4. คัดลอก **Channel secret** (จาก Basic settings) และ **Channel access token** (กด Issue)

### 2. ใส่ credentials ใน `.env`

```
LINE_CHANNEL_SECRET=<channel secret>
LINE_CHANNEL_ACCESS_TOKEN=<channel access token>
```

### 3. เปิดใช้งาน Webhook

ใน LINE Developers Console → **Messaging API** tab:

1. เปิด **Use webhook** → ON
2. ใส่ Webhook URL:
   ```
   https://<your-domain>/line/callback
   ```
3. กด **Verify** — ต้องได้ `200 OK`
4. ปิด **Auto-reply messages** และ **Greeting messages** (ไม่งั้นบอทตอบซ้ำ)

> **Local development:** ใช้ [ngrok](https://ngrok.com) เพื่อให้ LINE เข้าถึง localhost ได้
> ```bash
> ngrok http 8000
> # จะได้ URL เช่น https://xxxx.ngrok.io → ใช้ https://xxxx.ngrok.io/line/callback
> ```

### ตัวอย่างการตอบกลับของบอท

```
🚨 ฟิชชิ่ง (หลอกลวง) | ความเสี่ยง: สูงมาก (98%)

พบคำที่ใช้หลอกลวง: รางวัล | พบลิงก์ URL ในข้อความ

⚠️ คำเตือน: รางวัล, URL

📞 โทร 1599 สายด่วนไซเบอร์ (ฟรี 24 ชม.)
```

---

## CI/CD Workflow

### ภาพรวม Pipeline

```
git push main
    │
    ▼
1. Lint          — black, isort, flake8
2. Test          — pytest + coverage ≥ 70%
3. Docker Build  — ตรวจสอบว่า image build ได้
4. Deploy        — SSH เข้า GCP VM อัตโนมัติ
```

### สิ่งที่ Deploy ทำบน GCP VM

```
git pull origin main          ← ดึง code ใหม่
inject secrets → .env         ← อัปเดต GROQ / LINE keys
docker compose build          ← build image ใหม่
    │
    ├── models/best_model.joblib มีอยู่แล้ว?
    │       NO  → docker compose run --rm train
    │               (สร้างข้อมูล + เทรนโมเดล อัตโนมัติ)
    │       YES → ข้ามการเทรน
    │
docker compose up -d          ← เริ่ม api + app + mlflow
```

**ครั้งแรกที่ deploy:** โมเดลยังไม่มี → เทรนอัตโนมัติ (~2-3 นาที)
**deploy ครั้งถัดไป:** โมเดลมีอยู่แล้วบน VM disk → ข้ามการเทรน ทำให้เร็วขึ้น

### GitHub Secrets ที่ต้องตั้งค่า

ไปที่ **Settings → Secrets and variables → Actions** แล้วเพิ่ม:

| Secret | คำอธิบาย |
|--------|----------|
| `GCP_HOST` | IP หรือ hostname ของ GCP VM |
| `GCP_USER` | ชื่อ user สำหรับ SSH (เช่น `ubuntu`) |
| `GCP_SSH_KEY` | Private key สำหรับ SSH (ทั้งหมด รวม header) |
| `GCP_APP_PATH` | path ของโปรเจกต์บน VM (เช่น `/home/ubuntu/scamguard`) |
| `GROQ_API_KEY` | Groq API key |
| `LINE_CHANNEL_SECRET` | LINE channel secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE channel access token |

---

## เทรนโมเดลใหม่

**ผ่าน Docker (แนะนำ):**
```bash
docker compose run --rm train
docker compose restart api
```

**ผ่าน Python โดยตรง:**
```bash
python -m src.data.generator    # สร้างข้อมูลใหม่
python -m src.data.ingestion    # แบ่งชุดข้อมูล
python -m src.models.trainer    # เทรน + บันทึกผลใน MLflow
docker compose restart api
```

---

## รัน Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --cov=src --cov-report=term-missing
```
