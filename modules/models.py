from dataclasses import dataclass
from typing import Optional, Union

@dataclass
class InputData:
    # Required fields first
    region: str
    item_url: str
    # Optional fields follow
    item_name: Optional[str] = None
    image_url: Optional[str] = None
    post_category: Optional[str] = None
    warehouse_id: Optional[str] = None
    item_currency: Optional[str] = None
    item_price: Optional[float] = None
    discount: Optional[Union[float, str]] = None
    item_category: Optional[str] = None
    item_weight: Optional[float] = None
    payment_method: Optional[str] = None
    site: Optional[str] = None

@dataclass
class PostData(InputData):
    # Fields from InputData that become mandatory in PostData
    item_name: str
    image_url: str
    post_category: str
    warehouse_id: str
    item_currency: str
    item_price: float

    # New mandatory fields for PostData
    post_title: str
    post_content: str