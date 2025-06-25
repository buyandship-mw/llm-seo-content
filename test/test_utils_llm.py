import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from utils.llm import extract_and_parse_json


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("{\"a\": 1}", {"a": 1}),
        ("```json\n{\"a\": 1}\n```", {"a": 1}),
    ],
)
def test_extract_valid_json(input_str, expected):
    assert extract_and_parse_json(input_str) == expected


@pytest.mark.parametrize(
    "input_str",
    [None, "", "not json", "```json\n```"],
)
def test_extract_invalid_json(input_str):
    with pytest.raises(json.JSONDecodeError):
        extract_and_parse_json(input_str)
