"""Configuration loader for ScamGuard."""

from pathlib import Path
from typing import Any

import yaml


class Config:
    """Singleton configuration loader from YAML file."""

    _instance = None
    _config: dict = {}

    def __new__(cls, config_path: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path)
        return cls._instance

    def _load(self, config_path: str | None = None) -> None:
        if config_path is None:
            # Auto-detect project root
            root = Path(__file__).parent.parent.parent
            config_path = root / "configs" / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Traverse nested keys with dot notation support."""
        val = self._config
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key, default)
            else:
                return default
        return val

    def __getitem__(self, key: str) -> Any:
        return self._config[key]

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (useful for testing)."""
        cls._instance = None
        cls._config = {}


def get_project_root() -> Path:
    """Return absolute path to project root directory."""
    return Path(__file__).parent.parent.parent


def get_config(config_path: str | None = None) -> Config:
    """Get the global Config singleton."""
    return Config(config_path)
