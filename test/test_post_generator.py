import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.generation.post_generator import (
    _assemble_post_data,
    CTA_BY_WAREHOUSE,
)
from modules.core.models import PostData, Category, Interest, Warehouse

def _sample_data():
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
        region="US",
    )
    categories = [Category(label="cat", value=1)]
    interests = [Interest(label="int", value="int")]
    warehouses = [Warehouse(label="w", value="WH", currency="USD")]
    rates = {"USD": {"USD": 1.0}}
    parsed = {"item_name": "Item", "title": "Title", "content": "Base"}
    return parsed, item, categories, interests, warehouses, rates


def test_append_call_to_action():
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
    assert result["content"].endswith(CTA_BY_WAREHOUSE["DEFAULT"])

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