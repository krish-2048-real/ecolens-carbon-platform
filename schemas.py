"""EcoLens Pydantic Schemas.

Defines all data models used for API request/response validation and
Gemini structured output enforcement. These schemas guarantee type-safe,
deterministic JSON communication between frontend, backend, and LLM.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CarbonAnalysisRequest(BaseModel):
    """Schema for incoming text-based carbon analysis requests.

    Attributes:
        description: Free-text description of an activity, purchase,
            or lifestyle choice to analyze for carbon impact.
    """

    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Text description of the activity or item to analyze.",
        examples=["I drove 30 km to work in a petrol car today"],
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, v: str) -> str:
        """Validate that the description contains meaningful content.

        Args:
            v: The raw description string.

        Returns:
            The stripped description string.

        Raises:
            ValueError: If the description is blank after stripping.
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Description must contain meaningful text.")
        return stripped


class PersonalizedSwap(BaseModel):
    """A single actionable lifestyle alternative to reduce carbon output.

    Attributes:
        action: A concise, actionable swap recommendation.
        impact_reduction_percent: Estimated percentage reduction in carbon
            footprint if this swap is adopted.
        rationale: Brief explanation of why this swap helps.
    """

    action: str = Field(
        ...,
        description="Concise actionable recommendation (e.g., 'Take public transit').",
    )
    impact_reduction_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Estimated carbon reduction percentage from this swap.",
    )
    rationale: str = Field(
        ...,
        description="Brief explanation of the environmental benefit.",
    )


class CarbonAnalysisResult(BaseModel):
    """Core structured output schema enforced on the Gemini LLM response.

    This schema is passed directly to the Gemini API as ``response_schema``
    to guarantee deterministic, parseable JSON output.

    Attributes:
        category: The emission category (e.g., Transportation, Food, Energy).
        estimated_carbon_kg: Estimated CO2-equivalent emissions in kilograms.
        calculation_rationale: Step-by-step explanation of how the estimate
            was derived.
        personalized_swaps: List of 2-3 actionable lifestyle alternatives.
        accessibility_summary: Screen-reader-friendly plain-text summary
            of all carbon data, suitable for text-to-speech engines.
    """

    category: str = Field(
        ...,
        description="Emission category: Transportation, Food, Energy, Shopping, or Waste.",
    )
    estimated_carbon_kg: float = Field(
        ...,
        ge=0.0,
        description="Estimated CO2-equivalent emissions in kilograms.",
    )
    calculation_rationale: str = Field(
        ...,
        description="Step-by-step explanation of how the carbon estimate was calculated.",
    )
    personalized_swaps: List[PersonalizedSwap] = Field(
        ...,
        min_length=2,
        max_length=3,
        description="2-3 actionable lifestyle swap suggestions.",
    )
    accessibility_summary: str = Field(
        ...,
        min_length=10,
        description=(
            "A descriptive, text-to-speech friendly summary of the carbon "
            "analysis results for screen reader compliance."
        ),
    )


class CarbonAnalysisResponse(BaseModel):
    """Full API response wrapping the analysis result with metadata.

    Attributes:
        success: Whether the analysis completed successfully.
        input_type: Type of input that was analyzed.
        timestamp: ISO-8601 timestamp of when the analysis was performed.
        result: The carbon analysis result data.
        error: Optional error message if analysis failed.
    """

    success: bool = Field(default=True, description="Whether analysis succeeded.")
    input_type: Literal["text", "image"] = Field(
        ..., description="Type of input analyzed."
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp.",
    )
    result: Optional[CarbonAnalysisResult] = Field(
        default=None, description="The analysis result, if successful."
    )
    error: Optional[str] = Field(
        default=None, description="Error message if analysis failed."
    )


class HealthCheckResponse(BaseModel):
    """Response schema for the health check endpoint.

    Attributes:
        status: Current service status.
        version: Application version string.
        api_key_configured: Whether the Gemini API key is set.
    """

    status: str = Field(default="healthy", description="Service status.")
    version: str = Field(..., description="Application version.")
    api_key_configured: bool = Field(
        ..., description="Whether Gemini API key is configured."
    )
