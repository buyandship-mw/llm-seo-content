from dataclasses import dataclass, field
from typing import List, Optional, Union

@dataclass
class DemoData:
    post_id: str
    item_category: str
    category: List[str]
    item_name: str
    item_unit_price: float
    item_url: str
    site: str
    warehouse_id: str
    warehouse_location: str
    region: str
    title: str
    content: str
    like_count: int
    item_weight: Optional[Union[float, str]] = None
    discount: Optional[Union[float, str]] = None
    payment_method: Optional[str] = None
    hashtags: Optional[List[str]] = field(default_factory=list)
    item_unit_price_local: Optional[float] = None

    def __post_init__(self):
        # Placeholder for BNS endpoint call if you want to do it on object creation
        # For now, we'll assume it's populated later or during a processing step.
        pass

@dataclass
class InputData:
    item_category: str
    item_name: str
    item_unit_price: float
    item_url: str
    site: str
    warehouse_id: str
    warehouse_location: str
    region: str
    url_extracted_text: str
    discount: Optional[Union[float, str]] = None
    payment_method: Optional[str] = None
    item_weight: Optional[Union[float, str]] = None
    item_unit_price_local: Optional[float] = None

@dataclass
class OutputData:
    category: List[str]  # Multiple choice
    title: str
    content: str
    hashtags: Optional[List[str]] = field(default_factory=list)

@dataclass
class PostData:
    item_category: str
    category: List[str]  # Multiple choice
    item_name: str
    item_unit_price_usd: float # Specifically USD
    item_url: str
    site: str  # Shipment location
    warehouse_id: str
    warehouse_location: str
    region: str # Extracted from URL
    title: str
    content: str
    discount: Optional[Union[float, str]] = None
    payment_method: Optional[str] = None
    item_weight: Optional[Union[float, str]] = None
    hashtags: Optional[List[str]] = field(default_factory=list)