from modules.models import InputData, DemoData
from typing import List, Dict, Optional, Union

def retrieve_demos(input_data: InputData, num_examples: int, for_prompt_type: str) -> List[DemoData]:
    """
    Mock implementation of sampler.retrieve_demos.
    In a real scenario, this would query a vector DB or other retrieval system.
    """
    # print(f"MOCK SAMPLER: Retrieving {num_examples} demos for '{input_data.item_name}' for prompt type '{for_prompt_type}'.")
    demos = []
    for i in range(num_examples):
        demo_region = "HK" if i % 2 == 0 else "TW"
        demo_currency = "JPY" if demo_region == "HK" else "TWD"
        demo_price = 12000.0 if demo_currency == "JPY" else 2800.0
        demos.append(DemoData(
            post_id=f"demo_post_{i}_{for_prompt_type}", item_category="Electronics" if i % 2 == 0 else "Fashion Accessories",
            category="Electronics & Gadgets" if i % 2 == 0 else "Fashion & Apparel", item_name=f"Demo Item {i}",
            item_unit_price=demo_price, item_unit_price_currency=demo_currency, item_url=f"http://example.com/item{i}",
            site="DemoSite" if i % 2 == 0 else "StyleHub", warehouse_id=f"WH_DEMO_{i}",
            warehouse_location=f"{demo_region} Central Demo Warehouse", region=demo_region,
            title=f"Amazing Demo Item {i}!", content=f"Demo content for item {i}. Price {demo_price} {demo_currency}.",
            like_count=10 + i * 5, item_weight="0.5kg", discount="10%" if i % 2 == 0 else None
        ))
    return demos