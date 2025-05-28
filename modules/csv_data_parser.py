# Helper function to parse list-like strings from a CSV cell
from typing import Tuple, Optional, List, Union
from dataclasses import dataclass, field
import csv

from modules.data import DemoData, InputData

def parse_list_string(s: Optional[str], delimiter: str = '|') -> List[str]:
    """Parses a string containing delimited values into a list of strings."""
    if not s:
        return []
    return [item.strip() for item in s.split(delimiter) if item.strip()]

# Helper function to parse fields that can be a float or a string
def parse_flexible_numeric(value: Optional[str]) -> Optional[Union[float, str]]:
    """
    Tries to convert a string value to float. If it fails, returns the original string.
    Returns None if the input value is None or an empty/whitespace string.
    """
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return value # Return as string if float conversion fails

def parse_csv_to_demo_data(csv_file_path: str, list_delimiter: str = '|') -> List[DemoData]:
    """
    Parses a CSV file to create a list of DemoData objects.
    """
    demo_data_list: List[DemoData] = []
    with open(csv_file_path, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            row_num = i + 2 # For logging

            def get_val(key: str) -> Optional[str]:
                val = row.get(key)
                return val.strip() if val and val.strip() else None

            try:
                # --- Prepare fields for DemoData ---
                post_id_str = get_val('post_id')
                item_category_str = get_val('item_category')
                category_str = get_val('category') # Now a single string
                item_name_str = get_val('item_name')
                item_unit_price_str = get_val('item_unit_price')
                item_url_str = get_val('item_url')
                site_str = get_val('site')
                warehouse_id_str = get_val('warehouse_id')
                warehouse_location_str = get_val('warehouse_location')
                region_str = get_val('region')
                title_str = get_val('title')
                content_str = get_val('content')
                like_count_str = get_val('like_count')
                
                # Optional fields
                item_weight_str = get_val('item_weight')
                discount_str = get_val('discount')
                payment_method_str = get_val('payment_method')
                hashtags_str = get_val('hashtags') # Still uses parse_list_string

                # --- Type Conversions for Required Numeric Fields ---
                if item_unit_price_str is None:
                    raise ValueError("item_unit_price string is missing for DemoData")
                demo_price_val = float(item_unit_price_str)

                if like_count_str is None:
                    raise ValueError("like_count string is missing for DemoData")
                demo_like_count_val = int(like_count_str)

                # --- Instantiate DemoData ---
                demo_item = DemoData(
                    post_id=post_id_str if post_id_str is not None else "",
                    item_category=item_category_str if item_category_str is not None else "",
                    category=category_str if category_str is not None else "", # Pass as string
                    item_name=item_name_str if item_name_str is not None else "",
                    item_unit_price=demo_price_val,
                    item_url=item_url_str if item_url_str is not None else "",
                    site=site_str if site_str is not None else "",
                    warehouse_id=warehouse_id_str if warehouse_id_str is not None else "",
                    warehouse_location=warehouse_location_str if warehouse_location_str is not None else "",
                    region=region_str if region_str is not None else "",
                    title=title_str if title_str is not None else "",
                    content=content_str if content_str is not None else "",
                    like_count=demo_like_count_val,
                    item_weight=parse_flexible_numeric(item_weight_str),
                    discount=parse_flexible_numeric(discount_str),
                    payment_method=payment_method_str,
                    hashtags=parse_list_string(hashtags_str, list_delimiter)
                )
                demo_data_list.append(demo_item)
            except (ValueError, TypeError) as e:
                # print(f"Skipping DemoData for row {row_num}: {e}") # Uncomment for debugging
                pass
    return demo_data_list

def parse_csv_to_input_data(csv_file_path: str) -> List[InputData]:
    """
    Parses a CSV file to create a list of InputData objects.
    """
    input_data_list: List[InputData] = []
    with open(csv_file_path, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            row_num = i + 2 # For logging

            def get_val(key: str) -> Optional[str]:
                val = row.get(key)
                return val.strip() if val and val.strip() else None

            try:
                # --- Prepare fields for InputData ---
                item_category_str = get_val('item_category')
                item_name_str = get_val('item_name')
                item_unit_price_str = get_val('item_unit_price')
                item_url_str = get_val('item_url')
                site_str = get_val('site')
                warehouse_id_str = get_val('warehouse_id')
                warehouse_location_str = get_val('warehouse_location')
                region_str = get_val('region')
                url_extracted_text_str = get_val('url_extracted_text')

                # Optional fields
                discount_str = get_val('discount')
                payment_method_str = get_val('payment_method')
                item_weight_str = get_val('item_weight')

                # --- Type Conversions for Required Numeric Fields ---
                if item_unit_price_str is None:
                    raise ValueError("item_unit_price string is missing for InputData")
                input_price_val = float(item_unit_price_str)

                # --- Instantiate InputData ---
                input_item = InputData(
                    item_category=item_category_str if item_category_str is not None else "",
                    item_name=item_name_str if item_name_str is not None else "",
                    item_unit_price=input_price_val,
                    item_url=item_url_str if item_url_str is not None else "",
                    site=site_str if site_str is not None else "",
                    warehouse_id=warehouse_id_str if warehouse_id_str is not None else "",
                    warehouse_location=warehouse_location_str if warehouse_location_str is not None else "",
                    region=region_str if region_str is not None else "",
                    url_extracted_text=url_extracted_text_str if url_extracted_text_str is not None else "",
                    discount=parse_flexible_numeric(discount_str),
                    payment_method=payment_method_str,
                    item_weight=parse_flexible_numeric(item_weight_str)
                )
                input_data_list.append(input_item)
            except (ValueError, TypeError) as e:
                # print(f"Skipping InputData for row {row_num}: {e}") # Uncomment for debugging
                pass
    return input_data_list

if __name__ == '__main__':
    # Create a dummy CSV file for testing - 'media' column removed, 'category' is now single string
    dummy_csv_content_refactored = (
        "post_id,item_category,category,discount,item_name,item_unit_price,item_url,payment_method,site,warehouse_id,warehouse_location,item_weight,region,title,content,hashtags,like_count,url_extracted_text\n"
        # Valid row for DemoData
        "post1,Electronics,Audio Gadget,10%,Wireless Earbuds,79.99,http://example.com/earbuds,Credit Card,US-West,WH001,California,0.1kg,USA,Great Earbuds Review,These are amazing earbuds for the price.,#earbuds|#audio,1050,Full text about earbuds from URL\n"
        # Valid row for InputData (DemoData will fail: post_id, title, content, etc., are empty which __post_init__ catches)
        ",Books,Sci-Fi,,Space Opera Novel,19.99,http://example.com/book,,UK-South,WH002,London,0.5kg,UK,,,,#books,,Full text about the book\n"
        # Valid row for DemoData (url_extracted_text not used by DemoData)
        "post2,Fashion,Apparel,SALE,Cool T-Shirt,25.00,http://example.com/tshirt,PayPal,EU-Central,WH003,Berlin,0.2kg,GER,My New Favorite T-Shirt!,This t-shirt is so comfortable.,#fashion|#style,300,\n"
        # Invalid for both: item_name empty
        "post3,Home Goods,Decor,, ,9.99,http://example.com/vase,,,,,,,,,,,,\n"
        # Invalid for both: item_unit_price negative
        "post4,Sports,Gear,,Basketball,-5.00,http://example.com/ball,Credit Card,US-East,WH004,New York,0.6kg,USA,Best Basketball,Score big with this ball!,#sports,100,Some text\n"
        # Invalid for DemoData (like_count 'abc'); Valid for InputData.
        ",Music,Instruments,,Drum Set,299.99,http://example.com/drums,,,,,,,,My Drums,They are loud,#drums,abc,Drum text for testing\n" # Add item_category for input data
        # Invalid for both: item_unit_price missing
        "post6,Food,Snacks,,Chips,,http://example.com/chips,,,,,,,,Healthy Chips,Yummy,#chips,120,Chips text\n"
    )
    dummy_csv_file_path_refactored = 'dummy_data_refactored.csv'
    with open(dummy_csv_file_path_refactored, 'w', encoding='utf-8') as f:
        f.write(dummy_csv_content_refactored)

    print(f"Attempting to parse '{dummy_csv_file_path_refactored}' with separate parsers...")

    # Parse for DemoData
    demo_objects = parse_csv_to_demo_data(dummy_csv_file_path_refactored)
    print(f"\nSuccessfully parsed {len(demo_objects)} DemoData objects:")
    for i, item in enumerate(demo_objects):
        print(f"  DemoData {i+1}: post_id='{item.post_id}', category='{item.category}', title='{item.title[:20]}...'")

    # Parse for InputData
    input_objects = parse_csv_to_input_data(dummy_csv_file_path_refactored)
    print(f"\nSuccessfully parsed {len(input_objects)} InputData objects:")
    for i, item in enumerate(input_objects):
        print(f"  InputData {i+1}: item_name='{item.item_name}', item_category='{item.item_category}', url_text='{item.url_extracted_text[:20]}...'")