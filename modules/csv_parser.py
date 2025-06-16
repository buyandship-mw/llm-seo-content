from typing import Optional, List, Tuple, Union, TextIO
import csv

from modules.models import PostData

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

def load_warehouses_from_csv(filepath: str) -> List[Tuple[str,str]]:
    """Loads warehouses from a CSV file with two columns: 'warehouse_id' and 'region'."""
    warehouses: List[Tuple[str, str]] = []
    try:
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                warehouse_id = row.get('warehouse_id', '').strip()
                region = row.get('currency', '').strip()
                if warehouse_id and region:
                    warehouses.append((warehouse_id, region))
        print(f"Successfully loaded {len(warehouses)} warehouses from '{filepath}'.")
    except FileNotFoundError:
        print(f"Error: Warehouses file '{filepath}' not found.")
        raise # Or return empty list / handle as appropriate
    except Exception as e:
        print(f"An error occurred while loading warehouses from '{filepath}': {e}")
        raise # Or return empty list / handle as appropriate
    return warehouses

def parse_csv_to_post_data(file_input: Union[str, TextIO]) -> List[PostData]:
    """Parse CSV data into a list of ``PostData`` objects.

    The CSV headers should correspond to ``PostData`` field names. Any missing
    optional column will be filled with the default value from the dataclass.
    Numeric fields are converted when possible. Rows missing ``item_url`` are
    skipped.
    """
    post_data_list: List[PostData] = []
    
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
            
        required_headers = {'item_url'}
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

                # Required field
                item_url = row_dict['item_url']

                if not item_url or not item_url.strip():
                    print(f"Warning: Row {row_num}: Required field 'item_url' is empty. Skipping row.")
                    continue
                def to_float(val: Optional[str]) -> float:
                    if val is None:
                        return 0.0
                    try:
                        return float(val)
                    except ValueError:
                        print(f"Warning: Row {row_num}: Could not convert '{val}' to float. Using 0.0.")
                        return 0.0

                def to_int(val: Optional[str]) -> int:
                    if val is None:
                        return 0
                    try:
                        return int(float(val))
                    except ValueError:
                        print(f"Warning: Row {row_num}: Could not convert '{val}' to int. Using 0.")
                        return 0

                def to_bool(val: Optional[str]) -> bool:
                    if val is None:
                        return False
                    return val.strip().lower() in {"true", "1", "yes"}

                data_item = PostData(
                    title=get_cleaned_value('title') or '',
                    content=get_cleaned_value('content') or '',
                    user=get_cleaned_value('user') or PostData.user,
                    image_url=get_cleaned_value('image_url') or '',
                    status=get_cleaned_value('status') or PostData.status,
                    is_pinned=to_bool(get_cleaned_value('is_pinned')) if get_cleaned_value('is_pinned') is not None else PostData.is_pinned,
                    pinned_end_datetime=to_int(get_cleaned_value('pinned_end_datetime')) if get_cleaned_value('pinned_end_datetime') is not None else PostData.pinned_end_datetime,
                    pinned_expire_hours=to_int(get_cleaned_value('pinned_expire_hours')) if get_cleaned_value('pinned_expire_hours') is not None else PostData.pinned_expire_hours,
                    disable_comment=to_bool(get_cleaned_value('disable_comment')) if get_cleaned_value('disable_comment') is not None else PostData.disable_comment,
                    team_id=get_cleaned_value('team_id') or PostData.team_id,
                    category=to_int(get_cleaned_value('category')),
                    interest=get_cleaned_value('interest') or '',
                    payment_method=get_cleaned_value('payment_method'),
                    service=get_cleaned_value('service') or PostData.service,
                    discounted=get_cleaned_value('discounted'),
                    warehouse=get_cleaned_value('warehouse') or '',
                    item_url=item_url.strip(),
                    item_name=get_cleaned_value('item_name') or '',
                    item_unit_price=to_float(get_cleaned_value('item_unit_price')),
                    item_weight=to_float(get_cleaned_value('item_weight')),
                )
                post_data_list.append(data_item)

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
            
    return post_data_list
