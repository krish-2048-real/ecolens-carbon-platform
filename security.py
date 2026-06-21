"""EcoLens Security Module.

Implements the SecurityGuard class for input sanitization, prompt injection
detection, jailbreak phrase filtering, and file upload validation. Also
provides FastAPI middleware for automatic request interception.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from config import settings


# ---------------------------------------------------------------------------
# Injection & jailbreak pattern definitions
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS: List[str] = [
    # Direct instruction overrides
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"override\s+(all\s+)?instructions",
    r"new\s+instructions?\s*:",
    # System prompt extraction
    r"system\s*:\s*",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(your\s+)?system\s+prompt",
    r"print\s+(your\s+)?instructions",
    r"what\s+are\s+your\s+instructions",
    # Role manipulation
    r"you\s+are\s+now\b",
    r"act\s+as\b",
    r"pretend\s+(you\s+are|to\s+be)\b",
    r"roleplay\s+as\b",
    r"behave\s+as\b",
    r"simulate\s+being\b",
    # Jailbreak keywords
    r"\bdan\s+mode\b",
    r"\bdeveloper\s+mode\b",
    r"\bjailbreak\b",
    r"\bbypass\s+(safety|filter|restriction)",
    r"\bunfiltered\s+mode\b",
    r"\bno\s+restrictions?\b",
    r"\bdo\s+anything\s+now\b",
    # Encoding / obfuscation attempts
    r"base64\s*:",
    r"hex\s*:",
    r"rot13\s*:",
]

HTML_SCRIPT_PATTERNS: List[str] = [
    r"<\s*script\b[^>]*>",
    r"<\s*/\s*script\s*>",
    r"<\s*img\b[^>]*onerror\s*=",
    r"<\s*iframe\b",
    r"<\s*object\b",
    r"<\s*embed\b",
    r"javascript\s*:",
    r"on\w+\s*=\s*[\"']",
]

SHELL_METACHARACTER_PATTERNS: List[str] = [
    r";\s*(rm|del|cat|curl|wget|bash|sh|powershell)\b",
    r"\|\s*(rm|del|cat|curl|wget|bash|sh)\b",
    r"`[^`]+`",
    r"\$\([^)]+\)",
]

# Compile all patterns once at module load for performance
_COMPILED_INJECTION: List[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS
]
_COMPILED_HTML: List[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in HTML_SCRIPT_PATTERNS
]
_COMPILED_SHELL: List[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in SHELL_METACHARACTER_PATTERNS
]


class SecurityGuard:
    """Central security utility for input sanitization and validation.

    Provides methods to detect and neutralize prompt injection attempts,
    jailbreak phrases, HTML/script injection, and shell metacharacters
    before user input reaches the Gemini LLM.

    Attributes:
        max_file_size_bytes: Maximum allowed upload file size in bytes.
        allowed_extensions: Set of permitted file extensions.
    """

    def __init__(self) -> None:
        """Initialize SecurityGuard with settings from application config."""
        self.max_file_size_bytes: int = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        self.allowed_extensions: frozenset[str] = settings.ALLOWED_EXTENSIONS

    def sanitize_input(self, text: str) -> str:
        """Sanitize user input by removing malicious patterns.

        Strips prompt injection phrases, jailbreak keywords, HTML/script
        tags, and shell metacharacters from the input text.

        Args:
            text: Raw user input string to sanitize.

        Returns:
            Sanitized string with malicious patterns removed and
            whitespace normalized.
        """
        sanitized: str = text

        # Remove prompt injection and jailbreak patterns
        for pattern in _COMPILED_INJECTION:
            sanitized = pattern.sub("", sanitized)

        # Remove HTML/script injection
        for pattern in _COMPILED_HTML:
            sanitized = pattern.sub("", sanitized)

        # Remove shell metacharacters
        for pattern in _COMPILED_SHELL:
            sanitized = pattern.sub("", sanitized)

        # Normalize whitespace
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        return sanitized

    def is_safe(self, text: str) -> Tuple[bool, str]:
        """Check whether input text is safe for LLM processing.

        Scans the input against all known malicious patterns and returns
        a safety verdict with a reason if unsafe.

        Args:
            text: The raw input text to evaluate.

        Returns:
            A tuple of (is_safe, reason). If safe, reason is an empty
            string. If unsafe, reason describes the detected threat.
        """
        for pattern in _COMPILED_INJECTION:
            if pattern.search(text):
                return False, f"Prompt injection detected: {pattern.pattern}"

        for pattern in _COMPILED_HTML:
            if pattern.search(text):
                return False, f"HTML/script injection detected: {pattern.pattern}"

        for pattern in _COMPILED_SHELL:
            if pattern.search(text):
                return False, f"Shell metacharacter detected: {pattern.pattern}"

        return True, ""

    def validate_file_extension(self, filename: str) -> bool:
        """Validate that a file has a permitted extension.

        Args:
            filename: The original filename including extension.

        Returns:
            True if the file extension is in the allowed set, False otherwise.
        """
        if not filename or "." not in filename:
            return False
        ext: str = "." + filename.rsplit(".", 1)[-1].lower()
        return ext in self.allowed_extensions

    def validate_file_size(self, file_size: int) -> bool:
        """Validate that a file does not exceed the maximum allowed size.

        Args:
            file_size: File size in bytes.

        Returns:
            True if the file is within the size limit, False otherwise.
        """
        return 0 < file_size <= self.max_file_size_bytes


# Module-level singleton
security_guard = SecurityGuard()
