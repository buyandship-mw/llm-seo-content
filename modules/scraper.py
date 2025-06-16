# Updated root/modules/scraper.py with .md stub loading

import os
import re
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    raise EnvironmentError("FIRECRAWL_API_KEY not found in environment variables.")

API_URL = "https://api.firecrawl.dev/v1/scrape"

import re

import re

def extract_main_image_url(md: str) -> str:
    """
    Choose the best product image URL from markdown dump,
    then strip any nested prefix so you only get the real image URL.
    """
    # 1) find all candidate URLs ending in jpg/jpeg/png
    image_md    = re.findall(r'!\[[^\]]*\]\((https?://[^\)]+?\.(?:jpg|jpeg|png))\)', md)
    image_naked = re.findall(r'(https?://[^\s)]+?\.(?:jpg|jpeg|png))', md, re.I)
    all_images  = image_md + image_naked

    # 2) filter out obvious junk and require “/I/” in the path
    junk = ('sprite', 'icon', 'nav-', 'logo', 'sash', '_SS40_', 'global-', 'privacy')
    candidates = [
        u for u in all_images
        if not any(j in u for j in junk) and re.search(r'/I/', u)
    ]

    # 3) pick high-res if available, else the first candidate, else the first image, else None
    if candidates:
        high_res = [u for u in candidates if re.search(r'_(?:AC|SL|SX)', u)]
        selected = high_res[0] if high_res else candidates[0]
    elif all_images:
        selected = all_images[0]
    else:
        return None

    # 4) strip any nested prefix: if there are two "https://", keep only from the second one
    def strip_to_actual(url: str) -> str:
        occurrences = [m.start() for m in re.finditer(r'https?://', url)]
        if len(occurrences) > 1:
            return url[occurrences[1]:]
        return url

    return strip_to_actual(selected)

def extract_product_data(md: str, item_url: str, region: str) -> dict:
    """Extract structured product data from Firecrawl markdown."""
    image_url = extract_main_image_url(md)

    # Item name extraction
    header_matches = re.findall(r'^(?:#{1,2})\s*(.+)', md, re.MULTILINE)
    item_name = None
    if header_matches:
        long_headers = [h.strip() for h in header_matches if len(h.strip()) >= 15]
        item_name = max(long_headers, key=len) if long_headers else header_matches[-1].strip()

    if not item_name:
        lines = [l.strip() for l in md.split('\n')]
        text_lines = [
            l for l in lines
            if l and not l.startswith(('!','[','#','-','*','>','```'))
            and len(l) >= 15
            and not re.search(r'(menu|add to cart|customer review|visit the|shop|store|category)', l, re.I)
        ]
        item_name = max(text_lines, key=len) if text_lines else None

    if not item_name:
        for line in lines:
            if line and not line.startswith(('!','[','#','-','*','>','```')):
                if not re.match(r'^(商品説明|購入|配送|お支払|レビュー|特徴)', line):
                    item_name = line
                    break

    # Price & currency
    price_patterns = [
        # dollars variants
        (r'CA\$([0-9,\.]+)',        'CAD'),  # Canadian dollar (e.g. CA$123.45)
        (r'A\$([0-9,\.]+)',         'AUD'),  # Australian dollar (e.g. A$123.45)
        (r'NT\$([0-9,\.]+)',        'TWD'),  # New Taiwan dollar
        (r'HK\$([0-9,\.]+)',        'HKD'),  # Hong Kong dollar

        # common symbols
        (r'£([0-9,\.]+)',           'GBP'),  # British pound
        (r'€([0-9,\.]+)',           'EUR'),  # Euro
        (r'฿([0-9,\.]+)',           'THB'),  # Thai baht
        (r'Rp\s?([0-9,\.]+)',       'IDR'),  # Indonesian rupiah

        # CNY (using the “元” suffix)
        (r'([0-9,\.]+)\s*元',       'CNY'),

        # Japan
        (r'￥([0-9,]+)',            'JPY'),  # full-width yen sign
        (r'([0-9,]+)円',            'JPY'),  # yen with kanji

        # Korea
        (r'([0-9,]+)원',            'KRW'),  # won with hangul

        # finally a generic USD fallback
        (r'\$(\d[\d,\.]*)',         'USD'),
    ]
    source_price = None
    source_currency = None
    for pat, curr in price_patterns:
        m = re.search(pat, md)
        if m:
            val = m.group(1).replace(',', '')
            try:
                source_price = float(val)
                source_currency = curr
                break
            except ValueError:
                continue

    # Item weight (grams)
    weight = None
    weight_patterns = [
        (r'([0-9]+(?:\.[0-9]+)?)\s*(g|グラム|克)\b', 1),
        (r'([0-9]+(?:\.[0-9]+)?)\s*(kg|キロ|公斤)\b', 1000),
        (r'([0-9]+(?:\.[0-9]+)?)\s*(lb|磅)\b', 453.592),
    ]
    for pat, factor in weight_patterns:
        wm = re.search(pat, md, re.I)
        if wm:
            weight = round(float(wm.group(1)) * factor, 2)
            break
    
    data = {
        'item_url': item_url,
        'region': region,
        'image_url': image_url,
        'item_name': item_name,
        'source_price': source_price,
        'source_currency': source_currency,
        'item_weight': weight
    }
    print(f"Extracted data: {data}")
    return data

def scrape_and_extract(item_url: str, region: str) -> dict:
    """Fetch the page via Firecrawl and extract product data."""
    payload = {
        "url": item_url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        "removeBase64Images": True,
        "blockAds": True,
        "storeInCache": True
    }
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    md = data.get('markdown') or data.get('data', {}).get('markdown') or resp.text
    return extract_product_data(md, item_url, region)

if __name__ == "__main__":
    # Test stub: load sample markdown from file for quick local tests
    use_stub = True
    test_url = "https://dottodot.co.kr/product/detail.html?product_no=5395&cate_no=277"
    region = "hk"
    if use_stub:
        # Load from root/data/sample.md
        script_dir = os.path.dirname(__file__)
        sample_path = os.path.join(script_dir, '..', 'data', 'sample.md')
        with open(sample_path, 'r', encoding='utf-8') as f:
            sample_md = f.read()
        result = extract_product_data(sample_md, test_url, region)
    else:
        result = scrape_and_extract(test_url, region)