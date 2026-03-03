# GuardianShield Streamlit Frontend
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download PyThaiNLP corpus
RUN python -c "import pythainlp; pythainlp.corpus.download('words_th')" || true

COPY app/ ./app/
COPY src/ ./src/
COPY configs/ ./configs/
COPY .streamlit/ ./.streamlit/

ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false", \
     "--client.toolbarMode=viewer"]
