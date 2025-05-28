from dataclasses import dataclass, field
from typing import List, Optional, Union

@dataclass
class DemoData:
    post_id: str
    item_category: str
    category: str
    item_name: str
    item_unit_price: float
    item_unit_price_currency: str
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
        # Required string fields
        if not self.post_id: raise ValueError("DemoData: post_id cannot be empty.")
        if not self.item_category: raise ValueError("DemoData: item_category cannot be empty.")
        if not self.item_unit_price: raise ValueError("DemoData: item_unit_price cannot be empty.")
        if not self.item_unit_price_currency: raise ValueError("DemoData: item_unit_price_currency cannot be empty.")
        if not self.category: raise ValueError("DemoData: category cannot be empty.")
        if not self.item_name: raise ValueError("DemoData: item_name cannot be empty.")
        if not self.item_url: raise ValueError("DemoData: item_url cannot be empty.")
        # Potentially add URL validation here: from urllib.parse import urlparse; if not all([urlparse(self.item_url).scheme, urlparse(self.item_url).netloc]): raise ValueError("Invalid item_url format")
        if not self.site: raise ValueError("DemoData: site cannot be empty.")
        if not self.warehouse_id: raise ValueError("DemoData: warehouse_id cannot be empty.")
        if not self.warehouse_location: raise ValueError("DemoData: warehouse_location cannot be empty.")
        if not self.region: raise ValueError("DemoData: region cannot be empty.")
        if not self.title: raise ValueError("DemoData: title cannot be empty.")
        if not self.content: raise ValueError("DemoData: content cannot be empty.")
        if not self.like_count: raise ValueError("DemoData: like_count cannot be empty.")

        # Numeric validations
        if self.item_unit_price <= 0:
            raise ValueError("DemoData: item_unit_price must be positive.")
        if self.like_count < 0:
            raise ValueError("DemoData: like_count cannot be negative.")

        # Optional field validations (if they have specific rules when present)
        if isinstance(self.item_weight, float) and self.item_weight <= 0:
            raise ValueError("DemoData: item_weight, if numeric, must be positive.")
        # Similar for discount if it's a float

@dataclass
class InputData:
    item_category: str
    item_name: str
    item_unit_price: float
    item_unit_price_currency: str
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

    def __post_init__(self):
        # Required string fields
        if not self.item_category: raise ValueError("InputData: item_category cannot be empty.")
        if not self.item_name: raise ValueError("InputData: item_name cannot be empty.")
        if not self.item_unit_price: raise ValueError("DemoData: item_unit_price cannot be empty.")
        if not self.item_unit_price_currency: raise ValueError("DemoData: item_unit_price_currency cannot be empty.")
        if not self.item_url: raise ValueError("InputData: item_url cannot be empty.")
        if not self.site: raise ValueError("InputData: site cannot be empty.")
        if not self.warehouse_id: raise ValueError("InputData: warehouse_id cannot be empty.")
        if not self.warehouse_location: raise ValueError("InputData: warehouse_location cannot be empty.")
        if not self.region: raise ValueError("InputData: region cannot be empty.")
        if not self.url_extracted_text: raise ValueError("InputData: url_extracted_text cannot be empty.")

        # Numeric validations
        if self.item_unit_price <= 0:
            raise ValueError("InputData: item_unit_price must be positive.")

        # Optional field validations
        if isinstance(self.item_weight, float) and self.item_weight <= 0:
            raise ValueError("InputData: item_weight, if numeric, must be positive.")

@dataclass
class PostData:
    item_category: str
    category: str
    item_name: str
    item_unit_price: float
    item_unit_price_currency: str
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

    def __post_init__(self):
        # Required string fields
        if not self.item_category: raise ValueError("DemoData: item_category cannot be empty.")
        if not self.category: raise ValueError("DemoData: category cannot be empty.")
        if not self.item_name: raise ValueError("DemoData: item_name cannot be empty.")
        if not self.item_unit_price: raise ValueError("DemoData: item_unit_price cannot be empty.")
        if not self.item_unit_price_currency: raise ValueError("DemoData: item_unit_price_currency cannot be empty.")
        if not self.item_url: raise ValueError("DemoData: item_url cannot be empty.")
        # Potentially add URL validation here: from urllib.parse import urlparse; if not all([urlparse(self.item_url).scheme, urlparse(self.item_url).netloc]): raise ValueError("Invalid item_url format")
        if not self.site: raise ValueError("DemoData: site cannot be empty.")
        if not self.warehouse_id: raise ValueError("DemoData: warehouse_id cannot be empty.")
        if not self.warehouse_location: raise ValueError("DemoData: warehouse_location cannot be empty.")
        if not self.region: raise ValueError("DemoData: region cannot be empty.")
        if not self.title: raise ValueError("DemoData: title cannot be empty.")
        if not self.content: raise ValueError("DemoData: content cannot be empty.")

        # Numeric validations
        if self.item_unit_price <= 0:
            raise ValueError("PostData: item_unit_price must be positive.")

        # Optional field validations
        if self.payment_method is not None and not self.payment_method.strip():
            raise ValueError("PostData: payment_method, if provided, cannot be an empty string.")

        if isinstance(self.item_weight, float) and self.item_weight <= 0:
            raise ValueError("PostData: item_weight, if numeric, must be positive.")
        
        # TODO: Validate category is valid
        
        # Discount validation example: if it's a fixed amount (float), it should probably be positive.
        # If it's a percentage string like "10%", that's different.
        # This example assumes if it's a float, it's a positive discount amount.
        if isinstance(self.discount, float) and self.discount <= 0:
             raise ValueError("PostData: discount, if a numeric value, must be positive.")