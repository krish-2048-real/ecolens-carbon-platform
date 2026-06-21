"""EcoLens Gemini API Client.

Wraps the Google GenAI SDK to provide carbon footprint analysis from both
text descriptions and uploaded images. Enforces structured JSON output
through Pydantic schema constraints.
"""

from __future__ import annotations

from typing import Optional

from google import genai
from google.genai import types

from config import settings
from schemas import CarbonAnalysisResult
from security import security_guard


class GeminiClientError(Exception):
    """Custom exception for Gemini API client errors.

    Attributes:
        message: Human-readable error description.
        original_error: The underlying exception, if any.
    """

    def __init__(
        self, message: str, original_error: Optional[Exception] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.original_error = original_error


class EcoLensGeminiClient:
    """Client for carbon footprint analysis via Google Gemini API.

    Attributes:
        client: The underlying Google GenAI client instance.
        model_name: The Gemini model identifier.
        temperature: Sampling temperature for generation.
    """

    def __init__(self) -> None:
        """Initialize the Gemini client with application configuration.

        Raises:
            GeminiClientError: If the GEMINI_API_KEY is not configured.
        """
        if not settings.GEMINI_API_KEY:
            raise GeminiClientError(
                "GEMINI_API_KEY is not configured. "
                "Set it in your .env file or environment variables."
            )
        self.client: genai.Client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name: str = settings.MODEL_NAME
        self.temperature: float = settings.TEMPERATURE

    @staticmethod
    def _build_prompt(input_description: str) -> str:
        """Build an optimized system prompt for carbon analysis.

        Args:
            input_description: Sanitized user input.

        Returns:
            A formatted prompt string ready for the Gemini API.
        """
        return (
            "You are an expert carbon footprint analyst. Analyze the following "
            "activity or item and calculate its estimated CO2e emissions.\n\n"
            "RULES:\n"
            "1. Categorize into one of: Transportation, Food, Energy, Shopping, Waste.\n"
            "2. Provide estimated_carbon_kg as a realistic float in kilograms.\n"
            "3. Explain your calculation step-by-step in calculation_rationale.\n"
            "4. Suggest exactly 2-3 actionable personalized_swaps with realistic "
            "impact_reduction_percent values.\n"
            "5. Write an accessibility_summary: a natural descriptive sentence "
            "summarizing all results for screen readers (min 10 chars).\n\n"
            f"INPUT: {input_description}"
        )

    def analyze_text(self, description: str) -> CarbonAnalysisResult:
        """Analyze a text description for carbon footprint estimation.

        Args:
            description: Raw text description of the activity.

        Returns:
            CarbonAnalysisResult with structured carbon data.

        Raises:
            GeminiClientError: If API call or parsing fails.
        """
        sanitized: str = security_guard.sanitize_input(description)
        prompt: str = self._build_prompt(sanitized)
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=settings.MAX_OUTPUT_TOKENS,
                    response_mime_type="application/json",
                    response_schema=CarbonAnalysisResult,
                ),
            )
            if response.parsed is None:
                raise GeminiClientError("Gemini returned an empty response.")
            return response.parsed  # type: ignore[return-value]
        except GeminiClientError:
            raise
        except Exception as exc:
            raise GeminiClientError(
                f"Failed to analyze text: {exc}", original_error=exc
            ) from exc

    def analyze_image(self, image_bytes: bytes, mime_type: str) -> CarbonAnalysisResult:
        """Analyze an uploaded receipt/bill image for carbon footprint.

        Args:
            image_bytes: Raw bytes of the uploaded image file.
            mime_type: MIME type of the image.

        Returns:
            CarbonAnalysisResult with structured carbon data.

        Raises:
            GeminiClientError: If API call or parsing fails.
        """
        prompt: str = self._build_prompt(
            "Analyze the attached receipt or bill image. Identify products "
            "or activities and estimate their combined carbon footprint."
        )
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=settings.MAX_OUTPUT_TOKENS,
                    response_mime_type="application/json",
                    response_schema=CarbonAnalysisResult,
                ),
            )
            if response.parsed is None:
                raise GeminiClientError("Gemini returned an empty image response.")
            return response.parsed  # type: ignore[return-value]
        except GeminiClientError:
            raise
        except Exception as exc:
            raise GeminiClientError(
                f"Failed to analyze image: {exc}", original_error=exc
            ) from exc
