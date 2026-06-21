"""EcoLens Utility Helpers.

Provides file handling, data formatting, and accessibility narrative
generation utilities used across the application.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas import CarbonAnalysisResult, PersonalizedSwap


def format_carbon_output(result: CarbonAnalysisResult) -> Dict[str, Any]:
    """Format a CarbonAnalysisResult into a chart-ready dictionary.

    Transforms the structured analysis result into a format optimized
    for frontend visualization with Chart.js.

    Args:
        result: The structured carbon analysis result from Gemini.

    Returns:
        A dictionary containing chart_data, swaps list, and metadata
        suitable for direct JSON serialization to the frontend.
    """
    swaps_list: List[Dict[str, Any]] = [
        {
            "action": swap.action,
            "impact_reduction_percent": swap.impact_reduction_percent,
            "rationale": swap.rationale,
        }
        for swap in result.personalized_swaps
    ]

    return {
        "category": result.category,
        "estimated_carbon_kg": result.estimated_carbon_kg,
        "calculation_rationale": result.calculation_rationale,
        "accessibility_summary": result.accessibility_summary,
        "personalized_swaps": swaps_list,
        "chart_data": {
            "labels": [swap.action for swap in result.personalized_swaps],
            "reductions": [
                swap.impact_reduction_percent
                for swap in result.personalized_swaps
            ],
            "current_kg": result.estimated_carbon_kg,
        },
    }


def generate_accessibility_narrative(result: CarbonAnalysisResult) -> str:
    """Generate an enhanced text-to-speech friendly narrative.

    Creates a descriptive, natural-language summary suitable for screen
    readers that covers the carbon estimate, category, and top swap.

    Args:
        result: The structured carbon analysis result.

    Returns:
        A human-readable narrative string optimized for TTS engines.
    """
    top_swap: Optional[PersonalizedSwap] = result.personalized_swaps[0] if result.personalized_swaps else None
    swap_text: str = ""
    if top_swap:
        swap_text = (
            f" The top recommended alternative is: {top_swap.action}, "
            f"which could reduce your footprint by approximately "
            f"{top_swap.impact_reduction_percent:.0f} percent."
        )

    return (
        f"Your activity falls under the {result.category} category. "
        f"The estimated carbon footprint is {result.estimated_carbon_kg:.2f} "
        f"kilograms of CO2 equivalent.{swap_text} "
        f"{result.calculation_rationale}"
    )


def save_upload_file(file_bytes: bytes, filename: str, upload_dir: str) -> str:
    """Safely save uploaded file bytes to the upload directory.

    Creates the upload directory if it does not exist and writes the
    file bytes to disk.

    Args:
        file_bytes: The raw bytes of the uploaded file.
        filename: The original filename for the saved file.
        upload_dir: The directory path to save the file in.

    Returns:
        The absolute path to the saved file as a string.

    Raises:
        IOError: If the file cannot be written to disk.
    """
    dir_path: Path = Path(upload_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    safe_filename: str = Path(filename).name  # strip directory traversal
    file_path: Path = dir_path / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return str(file_path.resolve())


def cleanup_upload(filepath: str) -> None:
    """Remove a temporary upload file from disk.

    Silently ignores missing files to avoid errors during cleanup.

    Args:
        filepath: Absolute path to the file to remove.
    """
    try:
        os.remove(filepath)
    except OSError:
        pass
