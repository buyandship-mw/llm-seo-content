import os
from dotenv import load_dotenv
from firecrawl import JsonConfig, FirecrawlApp
from pydantic import BaseModel

# ─── Setup ──────────────────────────────────────────────────────────────────────

load_dotenv()
API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not API_KEY:
    raise EnvironmentError("FIRECRAWL_API_KEY not found")

APP = FirecrawlApp(api_key=API_KEY)

# ─── Schema for JSON Extraction ─────────────────────────────────────────────────

class RawJsonSchema(BaseModel):
    item_name_en: str
    item_image_url: str
    price: float
    currency_code_not_symbol: str
    item_weight_g: float

JSON_CONFIG = JsonConfig(schema=RawJsonSchema)

# ─── Helpers ────────────────────────────────────────────────────────────────────

def strip_query(url: str) -> str:
    """
    Remove query parameters from a URL, returning everything before the first '?'.
    """
    if not url:
        return url
    return url.split("?", 1)[0]

# ─── Parsers ────────────────────────────────────────────────────────────────────

def parse_metadata(meta: dict) -> dict:
    def get_first(keys):
        for k in keys:
            v = meta.get(k)
            if isinstance(v, list) and v:
                return v[0]
            if isinstance(v, str) and v.strip():
                return v
        return None

    return {
        "item_name":   get_first(["og:title", "twitter:title", "title", "ogTitle", "name"]),
        "image_url":   strip_query(get_first(["og:image", "ogImage", "twitter:image:src", "image"])),
        "source_price":    float(get_first(["price"])) if get_first(["price"]) else None,
        "source_currency": get_first(["priceCurrency", "currency"]),
        "item_weight":     float(get_first(["weight", "item_weight_g"])) if get_first(["weight", "item_weight_g"]) else None,
    }

def parse_json(json_data: dict) -> dict:
    return {
        "item_name":      json_data.get("item_name_en"),
        "image_url":      strip_query(json_data.get("item_image_url")),
        "source_price":   json_data.get("price"),
        "source_currency":json_data.get("currency_code_not_symbol"),
        "item_weight":    json_data.get("item_weight_g"),
    }

# ─── Single Extraction Call ────────────────────────────────────────────────────

def fetch_extraction(url: str, timeout: int = 120000):
    """
    Single Firecrawl call returning both metadata and JSON outputs.
    """
    resp = APP.scrape_url(
        url=url,
        formats=["json"],
        json_options=JSON_CONFIG,
        only_main_content=False,
        timeout=timeout
    )
    return resp.metadata, resp.json

# ─── Orchestrator ─────────────────────────────────────────────────────────────

def extract_product_data(url: str) -> dict:
    """
    Metadata-first extraction with JSON fallback, using a single API call.
    """
    meta, json_data = fetch_extraction(url)
    parsed_meta = parse_metadata(meta)
    parsed_json = parse_json(json_data)

    # Merge, preferring metadata values when present
    return {
        key: parsed_meta[key] if parsed_meta[key] not in (None, "") else parsed_json[key]
        for key in parsed_meta
    }

# ─── Example Usage ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    url = "https://item.rakuten.co.jp/stylife/nm8000/?variantId=94534918&s-id=ph_sp_itemname"
    product_info = extract_product_data(url)
    print(product_info)