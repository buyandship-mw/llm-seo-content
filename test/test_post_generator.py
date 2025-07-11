import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.generation.post_generator import (
    _assemble_post_data,
    CTA_BY_WAREHOUSE,
    COUNTRY_BY_WAREHOUSE,
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
        brand_name="",
        source_price=1.0,
        source_currency="USD",
        item_unit_price=1.0,
        item_weight=weight,
        region="US",
    )
    categories = [Category(label="cat", value=1)]
    interests = [Interest(label="int", value="int")]
    warehouses = [Warehouse(label="w", value="warehouse-4px-uspdx", currency="USD")]
    rates = {"USD": {"USD": 1.0}}
    parsed = {"item_name": "Item", "brand_name": "Brand", "title": "Title", "content": "Base"}
    return parsed, item, categories, interests, warehouses, rates


def test_append_call_to_action_without_weight():
    parsed, item, cats, ints, whs, rates = _sample_data()
    result = _assemble_post_data(
        parsed,
        "warehouse-4px-uspdx",
        item,
        cats,
        ints,
        whs,
        rates,
    )
    expected_cta = CTA_BY_WAREHOUSE["DEFAULT"].format(
        weight_blurb="",
        item_name="Item",
        country=COUNTRY_BY_WAREHOUSE.get("warehouse-4px-uspdx", ""),
    )
    assert result["content"].endswith(expected_cta)


def test_append_call_to_action_with_weight():
    parsed, item, cats, ints, whs, rates = _sample_data(weight=1000)
    result = _assemble_post_data(
        parsed,
        "warehouse-4px-uspdx",
        item,
        cats,
        ints,
        whs,
        rates,
    )
    expected_cta = CTA_BY_WAREHOUSE["DEFAULT"].format(
        weight_blurb="大約2.2磅，",
        item_name="Item",
        country=COUNTRY_BY_WAREHOUSE.get("warehouse-4px-uspdx", ""),
    )
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