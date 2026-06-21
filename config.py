"""EcoLens Application Configuration.

Centralizes all environment variables, model parameters, and application
constants. Validates critical settings at import time to fail fast on
misconfiguration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import FrozenSet

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration loaded from environment.

    Attributes:
        GEMINI_API_KEY: Google Gemini API key from environment.
        MODEL_NAME: Gemini model identifier for content generation.
        TEMPERATURE: Sampling temperature for deterministic JSON output.
        MAX_OUTPUT_TOKENS: Upper bound on generated token count.
        MAX_FILE_SIZE_MB: Maximum allowed upload file size in megabytes.
        ALLOWED_EXTENSIONS: Set of permitted file extensions for uploads.
        UPLOAD_DIR: Directory path for temporary file uploads.
        APP_TITLE: Display title for the application.
        APP_VERSION: Semantic version string.
    """

    GEMINI_API_KEY: str = ""
    MODEL_NAME: str = "gemini-2.0-flash"
    TEMPERATURE: float = 0.1
    MAX_OUTPUT_TOKENS: int = 1024
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: FrozenSet[str] = field(
        default_factory=lambda: frozenset(
            {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
        )
    )
    UPLOAD_DIR: str = "uploads"
    APP_TITLE: str = "EcoLens"
    APP_VERSION: str = "1.0.0"


def load_config() -> AppConfig:
    """Load and validate application configuration from environment variables.

    Reads the GEMINI_API_KEY from the process environment. If the key is
    absent, the config is still created (tests run mocked), but a warning
    is printed.

    Returns:
        AppConfig: A frozen dataclass containing all validated settings.

    Raises:
        None: Prints a warning instead of raising if key is missing, so
            test suites and health-check endpoints can still function.
    """
    api_key: str = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        print(
            "[EcoLens WARNING] GEMINI_API_KEY is not set. "
            "The application will start but LLM features will be unavailable."
        )

    config = AppConfig(GEMINI_API_KEY=api_key)

    # Ensure the upload directory exists
    upload_path = Path(config.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)

    return config


# Module-level singleton — imported by other modules
settings: AppConfig = load_config()
