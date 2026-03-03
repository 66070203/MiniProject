"""
Thai text preprocessor for GuardianShield.

Handles:
- URL, phone number, and special character removal
- Thai character normalization
- Word tokenization with PyThaiNLP
- Stopword removal
"""

import re
from pathlib import Path
from typing import Sequence

import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
URL_PATTERN = re.compile(
    r"(https?://|www\.)\S+|[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(/\S*)?",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(\+66|0)[0-9]{8,9}|0[0-9]{1,2}-[0-9]{3,4}-[0-9]{4}|1[0-9]{3,4}"
)
NUMBER_PATTERN = re.compile(r"\d+")
SPECIAL_CHAR_PATTERN = re.compile(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s.,!?%]")
WHITESPACE_PATTERN = re.compile(r"\s+")

# Thai characters range: \u0E00-\u0E7F


class ThaiTextPreprocessor:
    """
    Preprocesses raw Thai text messages for spam/phishing classification.

    Pipeline:
        raw text
        → lowercase (English only)
        → extract feature signals (URL count, phone count, etc.)
        → clean text (remove URLs, phones, special chars)
        → normalize whitespace
        → tokenize (PyThaiNLP)
        → remove stopwords (optional)
        → join tokens
    """

    def __init__(
        self,
        remove_stopwords: bool = True,
        engine: str = "newmm",
        keep_signals: bool = True,
    ):
        """
        Args:
            remove_stopwords: Whether to filter Thai stopwords
            engine: PyThaiNLP tokenizer engine (newmm, longest, etc.)
            keep_signals: Whether to retain signal token placeholders (URL_TOKEN, PHONE_TOKEN)
        """
        self.remove_stopwords = remove_stopwords
        self.engine = engine
        self.keep_signals = keep_signals
        self._stopwords: set[str] | None = None
        self._tokenize_func = None
        self._init_pythainlp()

    def _init_pythainlp(self) -> None:
        """Lazily initialize PyThaiNLP components."""
        try:
            from pythainlp.corpus.common import thai_stopwords
            from pythainlp.tokenize import word_tokenize

            self._tokenize_func = lambda text: word_tokenize(text, engine=self.engine)
            self._stopwords = thai_stopwords()
            logger.info(f"PyThaiNLP initialized with engine='{self.engine}'")
        except ImportError:
            logger.warning(
                "PyThaiNLP not installed. Falling back to whitespace tokenization."
            )
            self._tokenize_func = lambda text: text.split()
            self._stopwords = set()

    def extract_signals(self, text: str) -> dict:
        """Extract numerical signal features from raw text before cleaning."""
        return {
            "text_length": len(text),
            "word_count": len(text.split()),
            "url_count": len(URL_PATTERN.findall(text)),
            "phone_count": len(PHONE_PATTERN.findall(text)),
            "exclamation_count": text.count("!"),
            "number_ratio": len(NUMBER_PATTERN.findall(text))
            / max(len(text.split()), 1),
            "caps_ratio": sum(1 for c in text if c.isupper()) / max(len(text), 1),
        }

    def clean(self, text: str) -> str:
        """
        Clean raw text: remove noise, normalize, preserve Thai content.

        Steps:
            1. Replace URLs with placeholder token
            2. Replace phone numbers with placeholder token
            3. Lowercase English characters
            4. Remove special non-Thai characters
            5. Normalize whitespace
        """
        if not isinstance(text, str):
            return ""

        # Replace URLs and phones with tokens (preserves signal info for model)
        url_token = " URL " if self.keep_signals else " "
        phone_token = " PHONE " if self.keep_signals else " "
        text = URL_PATTERN.sub(url_token, text)
        text = PHONE_PATTERN.sub(phone_token, text)

        # Lowercase English
        text = text.lower()

        # Remove remaining special characters (keep Thai, Latin, digits, basic punct)
        text = SPECIAL_CHAR_PATTERN.sub(" ", text)

        # Normalize whitespace
        text = WHITESPACE_PATTERN.sub(" ", text).strip()
        return text

    def tokenize(self, text: str) -> list[str]:
        """Tokenize cleaned Thai text into word tokens."""
        tokens = self._tokenize_func(text)
        tokens = [t.strip() for t in tokens if t.strip()]
        if self.remove_stopwords and self._stopwords:
            tokens = [t for t in tokens if t not in self._stopwords]
        return tokens

    def process(self, text: str) -> str:
        """Full preprocessing pipeline: clean → tokenize → join."""
        cleaned = self.clean(text)
        tokens = self.tokenize(cleaned)
        return " ".join(tokens)

    def process_batch(self, texts: Sequence[str], verbose: bool = False) -> list[str]:
        """Process a batch of texts."""
        results = []
        for i, text in enumerate(texts):
            results.append(self.process(text))
            if verbose and (i + 1) % 1000 == 0:
                logger.info(f"Processed {i + 1}/{len(texts)} messages")
        return results

    def extract_signals_batch(self, texts: Sequence[str]) -> pd.DataFrame:
        """Extract signal features for a batch of texts."""
        return pd.DataFrame([self.extract_signals(t) for t in texts])


def preprocess_dataframe(
    df: pd.DataFrame,
    text_col: str = "text",
    preprocessor: ThaiTextPreprocessor | None = None,
) -> pd.DataFrame:
    """
    Apply preprocessing to a DataFrame, adding 'text_clean' column
    and appending extracted signal features.

    Args:
        df: Input DataFrame with text column
        text_col: Name of the raw text column
        preprocessor: ThaiTextPreprocessor instance (created if None)

    Returns:
        DataFrame with added 'text_clean' and signal feature columns
    """
    if preprocessor is None:
        config = get_config()
        preprocessor = ThaiTextPreprocessor(
            remove_stopwords=config["preprocessing"]["remove_stopwords"],
            engine=config["preprocessing"]["thai_engine"],
        )

    df = df.copy()

    # Clean text
    logger.info(f"Preprocessing {len(df)} messages...")
    df["text_clean"] = preprocessor.process_batch(
        df[text_col].fillna("").tolist(), verbose=True
    )

    # Extract signal features
    signals_df = preprocessor.extract_signals_batch(df[text_col].fillna("").tolist())
    df = pd.concat(
        [df.reset_index(drop=True), signals_df.reset_index(drop=True)], axis=1
    )

    # Filter out empty cleaned texts
    before = len(df)
    df = df[df["text_clean"].str.strip().str.len() > 0]
    if len(df) < before:
        logger.info(f"Removed {before - len(df)} rows with empty cleaned text.")

    logger.info(f"Preprocessing complete. {len(df)} messages retained.")
    return df
