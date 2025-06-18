import os
from dotenv import load_dotenv
from firecrawl import JsonConfig, FirecrawlApp
from pydantic import BaseModel

# Load environment variables from .env (do this once at import)
load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    raise EnvironmentError("FIRECRAWL_API_KEY not found in environment variables.")

APP = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

class ExtractSchema(BaseModel):
    item_name_en: str
    image_url: str
    country_of_origin_en: str
    price: float
    currency_code_not_symbol: str
    item_weight_g: float

def extract_product_data(
    url: str,
    schema=ExtractSchema,
    app=APP,
    timeout: int = 120_000
):
    """
    Extracts product data from a given URL using the provided schema and returns the JSON result.

    Schema of the expected data:
    - item_name_en: str
    - image_url: str
    - country_of_origin_en: str
    - price: float
    - currency_code_not_symbol: str
    - item_weight_g: float
    """
    json_config = JsonConfig(schema=schema)
    result = app.scrape_url(
        url=url,
        formats=["json"],
        json_options=json_config,
        only_main_content=False,
        timeout=timeout
    )
    return result.json

# Example usage:
if __name__ == "__main__":
    url = 'https://www.amazon.co.jp/dp/B0DB2G2FSG'
    data = extract_product_data(url)
    print(data)