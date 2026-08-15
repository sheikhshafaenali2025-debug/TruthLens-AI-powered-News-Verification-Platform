"""
utils/validators.py

Small, dependency-free request validation helpers shared by the route
handlers. Keeping validation here (rather than inline in routes) keeps the
Flask views focused on orchestration.
"""

from typing import Tuple, Optional


def validate_predict_payload(payload: Optional[dict], max_len: int, min_len: int) -> Tuple[bool, str]:
    """
    Validate the JSON body for POST /api/predict.

    Returns (is_valid, error_message). error_message is "" when valid.
    """
    if payload is None:
        return False, "Request body must be valid JSON."

    if not isinstance(payload, dict):
        return False, "Request body must be a JSON object."

    if "text" not in payload:
        return False, "Missing required field: 'text'."

    text = payload["text"]

    if not isinstance(text, str):
        return False, "'text' must be a string."

    stripped = text.strip()

    if len(stripped) == 0:
        return False, "'text' cannot be empty."

    if len(stripped) < min_len:
        return False, f"'text' is too short to analyze (minimum {min_len} characters)."

    if len(text) > max_len:
        return False, f"'text' exceeds maximum length of {max_len} characters."

    return True, ""
