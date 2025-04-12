"""
Utility functions for the workflow agent.
"""

import json
import logging
from typing import Any
from pathlib import Path


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging for the workflow agent.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger
    """
    logger = logging.getLogger("workflow_agent")
    logger.setLevel(getattr(logging, level.upper()))

    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, level.upper()))

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


def save_json(data: Any, filepath: str) -> None:
    """
    Save data to a JSON file.

    Args:
        data: Data to save
        filepath: Path to save to
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: str) -> Any:
    """
    Load data from a JSON file.

    Args:
        filepath: Path to load from

    Returns:
        Loaded data
    """
    with open(filepath, "r") as f:
        return json.load(f)


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}h {remaining_minutes}m"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def generate_id(prefix: str = "id") -> str:
    """
    Generate a unique ID with a prefix.

    Args:
        prefix: Prefix for the ID

    Returns:
        Unique ID string
    """
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def validate_email(email: str) -> bool:
    """
    Validate an email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid format
    """
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    # Replace invalid characters with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(". ")
    return sanitized or "unnamed"
