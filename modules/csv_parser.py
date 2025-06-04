from typing import Optional, List, Union, TextIO
import csv

from modules.models import InputData

def load_categories_from_csv(filepath: str) -> List[str]:
    """Loads categories from a single-column CSV file (one category per line)."""
    categories: List[str] = []
    try:
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip(): # Check for non-empty row and cell
                    categories.append(row[0].strip())
        print(f"Successfully loaded {len(categories)} categories from '{filepath}'.")
    except FileNotFoundError:
        print(f"Error: Categories file '{filepath}' not found.")
        raise # Or return empty list / handle as appropriate
    except Exception as e:
        print(f"An error occurred while loading categories from '{filepath}': {e}")
        raise # Or return empty list / handle as appropriate
    return categories

def parse_csv_to_input_data(file_input: Union[str, TextIO]) -> List[InputData]:
    """
    Parses a CSV file (or a file-like object) to create a list of InputData objects.

    Assumptions:
    - The CSV has a header row.
    - Header names in the CSV correspond to the field names in InputData.
    - 'region' and 'item_url' are required columns in the CSV.
    - Empty values for optional fields will be treated as None.
    - For 'discount', it attempts to convert to float; if it fails, it's kept as a string.
    - For 'item_price' and 'item_weight', it attempts to convert to float; if it fails,
      a warning is printed, and the value becomes None.
    """
    input_data_list: List[InputData] = []
    
    is_file_path = isinstance(file_input, str)
    if is_file_path:
        # We are given a file path
        file_obj = open(file_input, mode='r', newline='', encoding='utf-8')
    else:
        # We are given a file-like object
        file_obj = file_input

    try:
        reader = csv.DictReader(file_obj, skipinitialspace=True)
        
        # Check for essential headers
        if not reader.fieldnames:
            print("CSV file appears to be empty or has no headers.")
            return []
            
        required_headers = {'region', 'item_url'}
        present_headers = set(reader.fieldnames)
        if not required_headers.issubset(present_headers):
            missing = required_headers - present_headers
            raise ValueError(f"CSV is missing required headers: {', '.join(sorted(list(missing)))}")

        for row_num, row_dict in enumerate(reader, 1):
            try:
                # Helper to get value from row, treat empty string as None
                def get_cleaned_value(key: str) -> Optional[str]:
                    val = row_dict.get(key)
                    return val.strip() if val and val.strip() else None

                # Required fields
                region = row_dict['region']
                item_url = row_dict['item_url']

                if not region or not region.strip():
                    print(f"Warning: Row {row_num}: Required field 'region' is empty. Skipping row.")
                    continue
                if not item_url or not item_url.strip():
                    print(f"Warning: Row {row_num}: Required field 'item_url' is empty. Skipping row.")
                    continue
                
                # Optional float fields
                item_price_str = get_cleaned_value('item_price')
                item_price = None
                if item_price_str:
                    try:
                        item_price = float(item_price_str)
                    except ValueError:
                        print(f"Warning: Row {row_num}: Could not convert item_price '{item_price_str}' to float. Using None.")

                item_weight_str = get_cleaned_value('item_weight')
                item_weight = None
                if item_weight_str:
                    try:
                        item_weight = float(item_weight_str)
                    except ValueError:
                        print(f"Warning: Row {row_num}: Could not convert item_weight '{item_weight_str}' to float. Using None.")
                
                # Discount field (Union[float, str])
                discount_str = get_cleaned_value('discount')
                discount_value: Optional[Union[float, str]] = None
                if discount_str:
                    try:
                        discount_value = float(discount_str)
                    except ValueError:
                        discount_value = discount_str # Keep as string if float conversion fails

                data_item = InputData(
                    region=region.strip(),
                    item_url=item_url.strip(),
                    item_name=get_cleaned_value('item_name'),
                    post_category=get_cleaned_value('post_category'),
                    image_url=get_cleaned_value('image_url'),
                    warehouse_id=get_cleaned_value('warehouse_id'),
                    item_currency=get_cleaned_value('item_currency'),
                    item_price=item_price,
                    discount=discount_value,
                    item_category=get_cleaned_value('item_category'),
                    item_weight=item_weight,
                    payment_method=get_cleaned_value('payment_method'),
                    site=get_cleaned_value('site')
                )
                input_data_list.append(data_item)

            except KeyError as e:
                # This might occur if a row is severely malformed and DictReader yields unexpected keys,
                # though the header check should mitigate this for known headers.
                print(f"Warning: Row {row_num}: Missing expected key {e} in CSV row data. Skipping row.")
                continue
            except Exception as e:
                # Catch any other unexpected error during row processing
                print(f"Warning: Row {row_num}: An unexpected error occurred: {e}. Skipping row.")
                continue
                
    finally:
        if is_file_path:
            file_obj.close()
            
    return input_data_list