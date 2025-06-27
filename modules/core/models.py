from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    """Represents a selectable post category."""
    label: str
    value: int


@dataclass
class Interest:
    """Represents a user's area of interest."""
    label: str
    value: str

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
    source_price: float
    source_currency: str
    item_unit_price: float
    region: str
    item_weight: Optional[float] = None
    category_label: str = None
    brand_name: str = None
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
    """Represents a fulfillment warehouse."""
    label: str
    value: str
    currency: str


@dataclass
class AbortedGeneration:
    item_url: str
    region: str
    abort_reason: str
