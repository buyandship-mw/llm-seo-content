from dataclasses import dataclass
from typing import Optional

@dataclass
class PostData:
    title: str
    content: str
    image_url: str
    category: int
    interest: str
    warehouse: str
    item_url: str
    item_name: str
    item_unit_price: float
    item_weight: float
    user: str = "B2kKF5R47K8VpY3ynBh9CB"
    status: str = "draft"
    is_pinned: bool = False
    pinned_end_datetime: int = 0
    pinned_expire_hours: int = 0
    disable_comment: bool = False
    team_id: str = "hk"
    payment_method: Optional[str] = None
    service: str = "buyforyou"
    discounted: Optional[str] = None

@dataclass
class Warehouse:
    id: str
    currency: str