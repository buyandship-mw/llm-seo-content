import csv
from dataclasses import dataclass
from typing import List

from modules.models import PostData

def write_post_data_to_csv(filepath: str, post_data_list: List[PostData]) -> None:
    """Writes a list of PostData objects to a CSV file."""
    if not post_data_list:
        print("No data to write to CSV.")
        return

    # Use dataclasses.fields to get field names if PostData is a dataclass
    # Or define fieldnames explicitly
    fieldnames = [f.name for f in dataclass.fields(PostData)] if hasattr(PostData, "__dataclass_fields__") else list(post_data_list[0].__dict__.keys())

    try:
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for post_data_item in post_data_list:
                writer.writerow(post_data_item.__dict__) # Assumes PostData can be converted to dict
        print(f"Successfully wrote {len(post_data_list)} items to '{filepath}'.")
    except Exception as e:
        print(f"An error occurred while writing data to '{filepath}': {e}")
        raise