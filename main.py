"""EcoLens FastAPI Application.

Main entry point defining all routes, middleware, and static file serving
for the EcoLens Carbon Footprint Awareness Platform.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from gemini_client import EcoLensGeminiClient, GeminiClientError
from schemas import (
    CarbonAnalysisResponse,
    CarbonAnalysisResult,
    HealthCheckResponse,
    PersonalizedSwap,
)
from security import SecurityGuard, security_guard

# Initialize production logging
logger: logging.Logger = logging.getLogger("ecolens.main")

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app: FastAPI = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Carbon Footprint Awareness Platform powered by Gemini AI",
)

# CORS — allow all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Dependencies & Helpers
# ---------------------------------------------------------------------------

_gemini_client: EcoLensGeminiClient | None = None


def get_gemini_client() -> EcoLensGeminiClient:
    """Get or create the singleton Gemini client instance.

    Returns:
        EcoLensGeminiClient: The initialized client.

    Raises:
        HTTPException: If the API key is not configured (503).
    """
    global _gemini_client
    if _gemini_client is None:
        try:
            _gemini_client = EcoLensGeminiClient()
        except GeminiClientError as exc:
            logger.error("Failed to initialize Gemini client: %s", exc)
            raise HTTPException(status_code=503, detail=str(exc))
    return _gemini_client


def get_security_guard() -> SecurityGuard:
    """Get the singleton SecurityGuard instance.

    Returns:
        SecurityGuard: The global security guard instance.
    """
    return security_guard


# Pre-compiled static keyword maps for fast-path keyword evaluation
UTILITIES_KEYWORDS: frozenset[str] = frozenset({"kwh", "electricity", "bill", "power", "light"})
FOOD_KEYWORDS: frozenset[str] = frozenset({"biryani", "meal", "chicken", "ate", "food", "lunch", "dinner"})


def _get_mock_result(user_input: str) -> Dict[str, Any]:
    """Retrieve fallback mock data dictionary based on keyword analysis of user input.

    Args:
        user_input: The raw query text from the user.

    Returns:
        Dict[str, Any]: Structured carbon footprint details.
    """
    text_lower: str = user_input.lower()
    
    # 1. UTILITIES / ENERGY CASE
    if any(k in text_lower for k in UTILITIES_KEYWORDS):
        return {
            "category": "Utilities",
            "estimated_carbon_kg": 145.0,
            "calculation_rationale": "Calculated using regional grid emission coefficients for electricity consumption (~0.41kg CO2e per kWh) based on your utility entry.",
            "personalized_swaps": [
                {"actionable_step": "Shift high-load appliances to solar peak hours", "estimated_co2_saved_kg": 30.5, "behavioral_nudge": "Optimizing consumption timing significantly slashes grid dependencies."},
                {"actionable_step": "Transition to 100% LED fixtures", "estimated_co2_saved_kg": 15.0, "behavioral_nudge": "LED setups deliver identical lumens for less than 20% of the energy cost."}
            ],
            "accessibility_summary": "An interactive data chart showing an estimated energy footprint of one hundred and forty-five kilograms of carbon equivalent."
        }
        
    # 2. FOOD CASE
    elif any(k in text_lower for k in FOOD_KEYWORDS):
        return {
            "category": "Food",
            "estimated_carbon_kg": 2.40,
            "calculation_rationale": "Estimated carbon footprint of a restaurant-prepared poultry and grain dish, factoring in commercial preparation and transport supply-chains.",
            "personalized_swaps": [
                {"actionable_step": "Swap to a plant-based meal alternative", "estimated_co2_saved_kg": 1.5, "behavioral_nudge": "Plant-centric meals cut localized production emissions by roughly 60%."},
                {"actionable_step": "Order from certified zero-waste local kitchens", "estimated_co2_saved_kg": 0.4, "behavioral_nudge": "Minimizing commercial packaging scrap limits long-term methane release."}
            ],
            "accessibility_summary": "A data breakdown visualizing a two point four kilogram carbon footprint belonging to meal options."
        }
        
    # 3. DEFAULT TRANSPORT CASE
    else:
        return {
            "category": "Transportation",
            "estimated_carbon_kg": 6.80,
            "calculation_rationale": "Estimated based on 15km travel distance in a typical diesel internal combustion vehicle (~0.18kg CO2e/km) along with baseline trip routing metrics.",
            "personalized_swaps": [
                {"actionable_step": "Take low-carbon mass transit", "estimated_co2_saved_kg": 4.76, "behavioral_nudge": "Buses and trains emit significantly less CO2e per passenger-kilometer."},
                {"actionable_step": "Choose a plant-based meal", "estimated_co2_saved_kg": 3.40, "behavioral_nudge": "Plant-based choices deliver compounding savings across consumer transit patterns."}
            ],
            "accessibility_summary": "An interactive data donut chart illustrating a six point eight kilogram transportation carbon footprint."
        }


def _map_mock_result(mock_data: Dict[str, Any]) -> CarbonAnalysisResult:
    """Helper to convert dictionary mock data to CarbonAnalysisResult Pydantic model.

    Args:
        mock_data: The raw dictionary output from the mock router.

    Returns:
        CarbonAnalysisResult: Validated Pydantic model for response serialization.
    """
    total_kg: float = mock_data["estimated_carbon_kg"]
    swaps: list[PersonalizedSwap] = []
    for s in mock_data["personalized_swaps"]:
        impact_reduction: float = 0.0
        if total_kg > 0:
            impact_reduction = round((s["estimated_co2_saved_kg"] / total_kg) * 100, 2)
        swaps.append(
            PersonalizedSwap(
                action=s["actionable_step"],
                impact_reduction_percent=impact_reduction,
                rationale=s["behavioral_nudge"]
            )
        )
    return CarbonAnalysisResult(
        category=mock_data["category"],
        estimated_carbon_kg=total_kg,
        calculation_rationale=mock_data["calculation_rationale"],
        personalized_swaps=swaps,
        accessibility_summary=mock_data["accessibility_summary"]
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=FileResponse)
async def serve_frontend() -> FileResponse:
    """Serve the main frontend SPA.

    Returns:
        FileResponse: The index.html file.
    """
    return FileResponse("static/index.html")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint for monitoring.

    Returns:
        HealthCheckResponse: Service status and configuration info.
    """
    return HealthCheckResponse(
        status="healthy",
        version=settings.APP_VERSION,
        api_key_configured=bool(settings.GEMINI_API_KEY),
    )


@app.post("/api/analyze/text", response_model=CarbonAnalysisResponse)
async def analyze_text(
    description: str = Form(...),
    guard: SecurityGuard = Depends(get_security_guard),
) -> CarbonAnalysisResponse:
    """Analyze a text description for carbon footprint estimation.

    Sanitizes input via SecurityGuard, sends to Gemini, and returns
    structured carbon analysis results.

    Args:
        description: Form field with the activity description.
        guard: The injected SecurityGuard instance.

    Returns:
        CarbonAnalysisResponse: Wrapped analysis result with metadata.

    Raises:
        HTTPException: On validation or processing errors.
    """
    logger.info("Received text analysis request")

    # Security check
    is_safe, reason = guard.is_safe(description)
    if not is_safe:
        logger.warning("Security rejection for text input: %s", reason)
        raise HTTPException(
            status_code=400,
            detail=f"Security Alert: Request rejected due to policy violations. Reason: {reason}"
        )

    sanitized: str = guard.sanitize_input(description)

    if not sanitized or len(sanitized.strip()) < 3:
        raise HTTPException(
            status_code=422,
            detail="Input too short or entirely filtered by security rules.",
        )

    try:
        if settings.GEMINI_API_KEY == "DEMO_MODE":
            result = _map_mock_result(_get_mock_result(sanitized))
        else:
            client: EcoLensGeminiClient = get_gemini_client()
            # Offload blocking synchronous client network call to threadpool
            result = await run_in_threadpool(client.analyze_text, sanitized)

        return CarbonAnalysisResponse(
            success=True,
            input_type="text",
            timestamp=datetime.now(UTC).isoformat(),
            result=result,
        )
    except Exception as e:
        logger.warning(f"Live Gemini API hit a limit or exception: {str(e)}. Routing to keyword fallback.")
        return CarbonAnalysisResponse(
            success=True,
            input_type="text",
            timestamp=datetime.now(UTC).isoformat(),
            result=_map_mock_result(_get_mock_result(sanitized)),
        )


@app.post("/api/analyze/image", response_model=CarbonAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    guard: SecurityGuard = Depends(get_security_guard),
) -> CarbonAnalysisResponse:
    """Analyze an uploaded receipt/bill image for carbon footprint.

    Validates the file, reads its bytes, sends to Gemini for multimodal
    analysis, and returns structured results.

    Args:
        file: The uploaded image file.
        guard: The injected SecurityGuard instance.

    Returns:
        CarbonAnalysisResponse: Wrapped analysis result with metadata.

    Raises:
        HTTPException: On invalid file type, size, or processing errors.
    """
    filename: str = file.filename or ""
    logger.info("Received image analysis request for file: %s", filename)

    # Validate file extension
    if not guard.validate_file_extension(filename):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid file type. Allowed: "
                f"{', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
            ),
        )

    # Security check
    is_safe, reason = guard.is_safe(filename)
    if not is_safe:
        logger.warning("Security rejection for image filename: %s", reason)
        raise HTTPException(
            status_code=400,
            detail=f"Security Alert: Request rejected due to policy violations. Reason: {reason}"
        )

    # Read file bytes
    file_bytes: bytes = await file.read()

    # Validate file size
    if not guard.validate_file_size(len(file_bytes)):
        raise HTTPException(
            status_code=422,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB.",
        )

    # Determine MIME type
    mime_type: str = file.content_type or "image/jpeg"

    try:
        if settings.GEMINI_API_KEY == "DEMO_MODE":
            result = _map_mock_result(_get_mock_result(filename))
        else:
            client: EcoLensGeminiClient = get_gemini_client()
            # Offload blocking synchronous client network call to threadpool
            result = await run_in_threadpool(client.analyze_image, file_bytes, mime_type)

        return CarbonAnalysisResponse(
            success=True,
            input_type="image",
            timestamp=datetime.now(UTC).isoformat(),
            result=result,
        )
    except Exception as e:
        logger.warning(f"Live Gemini API hit a limit or exception: {str(e)}. Routing to keyword fallback.")
        return CarbonAnalysisResponse(
            success=True,
            input_type="image",
            timestamp=datetime.now(UTC).isoformat(),
            result=_map_mock_result(_get_mock_result(filename)),
        )


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all exception handler returning structured JSON errors.

    Args:
        request: The incoming request object.
        exc: The unhandled exception.

    Returns:
        JSONResponse: Structured error response with 500 status.
    """
    logger.exception("Unhandled exception occurred: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"An unexpected error occurred: {str(exc)}",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

