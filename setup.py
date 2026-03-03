"""GuardianShield package setup."""
from setuptools import setup, find_packages

setup(
    name="guardianshield",
    version="1.0.0",
    description="AI-powered spam/phishing detection for elderly users",
    author="GuardianShield Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "scikit-learn>=1.3.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pythainlp>=5.0.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "streamlit>=1.28.0",
        "mlflow>=2.8.0",
        "pydantic>=2.0.0",
        "pandera>=0.17.0",
        "sqlalchemy>=2.0.0",
        "pyyaml>=6.0.0",
    ],
)
