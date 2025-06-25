import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.generation.post_generator import (
    _assemble_post_data,
    CTA_BY_WAREHOUSE,
    _build_comprehensive_llm_prompt,
    ABORT_FIELD,
    ABORT_REASON,
)
from modules.core.models import PostData, Category, Interest, Warehouse

def _sample_data(weight=None):
    item = PostData(
        title="",
        content="",
        image_url="http://img",
        category=1,
        interest="",
        warehouse="",
        item_url="http://example.com",
        item_name="",
        source_price=1.0,
        source_currency="USD",
        item_unit_price=1.0,
        item_weight=weight,
        region="US",
    )
    categories = [Category(label="cat", value=1)]
    interests = [Interest(label="int", value="int")]
    warehouses = [Warehouse(label="w", value="WH", currency="USD")]
    rates = {"USD": {"USD": 1.0}}
    parsed = {"item_name": "Item", "title": "Title", "content": "Base"}
    return parsed, item, categories, interests, warehouses, rates


def test_append_call_to_action_without_weight():
    parsed, item, cats, ints, whs, rates = _sample_data()
    result = _assemble_post_data(
        parsed,
        "WH",
        item,
        cats,
        ints,
        whs,
        rates,
    )
    expected_cta = CTA_BY_WAREHOUSE["DEFAULT"].format(weight_blurb="")
    assert result["content"].endswith(expected_cta)


def test_append_call_to_action_with_weight():
    parsed, item, cats, ints, whs, rates = _sample_data(weight=1000)
    result = _assemble_post_data(
        parsed,
        "WH",
        item,
        cats,
        ints,
        whs,
        rates,
    )
    expected_cta = CTA_BY_WAREHOUSE["DEFAULT"].format(weight_blurb="大約2.2磅，")
    assert result["content"].endswith(expected_cta)

def test_assemble_post_data_raises_on_zero_price():
    parsed, item, cats, ints, whs, rates = _sample_data()
    item.source_price = 0.0
    import pytest
    with pytest.raises(ValueError):
        _assemble_post_data(
            parsed,
            "WH",
            item,
            cats,
            ints,
            whs,
            rates,
        )


def test_assemble_post_data_raises_on_none_price():
    parsed, item, cats, ints, whs, rates = _sample_data()
    item.source_price = None
    import pytest
    with pytest.raises(ValueError):
        _assemble_post_data(
            parsed,
            "WH",
            item,
            cats,
            ints,
            whs,
            rates,
        )


def test_prompt_includes_abort_instruction():
    parsed, item, cats, ints, whs, rates = _sample_data()
    item.region = "HK"
    prompt, _ = _build_comprehensive_llm_prompt(item, cats, ints)
    assert ABORT_FIELD in prompt
    assert ABORT_REASON in prompt

    # abort check should appear before workflow instructions
    workflow_index = prompt.index("STEP-BY-STEP WORKFLOW")
    abort_index = prompt.index(ABORT_FIELD)
    assert abort_index < workflow_index

