# GuardianShield Makefile
# Usage: make <target>

.PHONY: help install install-dev data train test lint format docker-up docker-down clean

help:
	@echo "GuardianShield — Available commands:"
	@echo ""
	@echo "  Setup:"
	@echo "    make install       Install production dependencies"
	@echo "    make install-dev   Install development dependencies"
	@echo ""
	@echo "  Data & Training:"
	@echo "    make data          Generate dataset + run ingestion pipeline"
	@echo "    make train         Train all models with MLflow tracking"
	@echo "    make pipeline      Run full pipeline (data + train)"
	@echo ""
	@echo "  Testing:"
	@echo "    make test          Run pytest with coverage"
	@echo "    make test-fast     Run tests (no coverage)"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint          Run flake8 + isort check"
	@echo "    make format        Auto-format with black + isort"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-up     Start all services (docker compose up)"
	@echo "    make docker-down   Stop all services"
	@echo "    make docker-build  Rebuild Docker images"
	@echo ""
	@echo "  Dev Servers:"
	@echo "    make api           Start FastAPI server (dev)"
	@echo "    make app           Start Streamlit app"
	@echo "    make mlflow        Start MLflow UI"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean         Remove generated files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

data:
	@echo "==> Running data pipeline..."
	python -m src.data.generator
	python -m src.data.ingestion
	@echo "==> Data pipeline complete."

train:
	@echo "==> Training models with MLflow..."
	python -m src.models.trainer
	@echo "==> Training complete."

pipeline: data train
	@echo "==> Full pipeline complete."

test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-fast:
	pytest tests/ -v --tb=short -x

lint:
	flake8 src/ tests/ app/ --max-line-length=100 --extend-ignore=E203,W503
	isort --check-only src/ tests/ app/

format:
	black src/ tests/ app/
	isort src/ tests/ app/

docker-up:
	docker compose up -d
	@echo "Services started:"
	@echo "  Streamlit: http://localhost:8501"
	@echo "  FastAPI:   http://localhost:8000/docs"
	@echo "  MLflow:    http://localhost:5000"

docker-down:
	docker compose down

docker-build:
	docker compose build --no-cache

api:
	uvicorn src.api.main:app --reload --port 8000 --host 0.0.0.0

app:
	streamlit run app/streamlit_app.py --server.port 8501 --client.toolbarMode viewer

mlflow:
	mlflow ui --port 5000

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "Cleaned build artifacts."
