import json
from typing import Any, Optional


def extract_and_parse_json(raw_response_text: Optional[str]) -> Any:
    """Cleans a raw string response presumed to contain JSON and parses it.

    This helper removes surrounding Markdown code fences (e.g. ````json` ... ```)
    if present, then attempts to parse the remaining string as JSON.

    Args:
        raw_response_text: The raw string response from an external source. Can
            be ``None`` or empty.

    Returns:
        The parsed JSON object such as ``dict`` or ``list``.

    Raises:
        json.JSONDecodeError: If parsing fails or the cleaned string is empty.
    """
    if not raw_response_text:
        raise json.JSONDecodeError(
            "Input response string is empty or None.", raw_response_text or "", 0
        )

    clean_json_string = raw_response_text.strip()

    if clean_json_string.startswith("```json"):
        clean_json_string = clean_json_string[len("```json"):].strip()
    if clean_json_string.endswith("```"):
        clean_json_string = clean_json_string[:-len("```")].strip()

    if not clean_json_string:
        raise json.JSONDecodeError("Cleaned JSON string is empty.", raw_response_text, 0)

    return json.loads(clean_json_string)
