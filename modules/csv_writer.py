# csv_writer.py
import csv
from typing import List
from dataclasses import fields, is_dataclass

from modules.models import PostData

def write_post_data_to_csv(filepath: str, post_data_list: List[PostData]) -> None:
    """Writes a list of PostData objects to a CSV file."""
    if not post_data_list:
        raise ValueError("No data to write to CSV.")

    # Correctly get field names using the imported 'fields' function and verify PostData is a dataclass.
    if is_dataclass(PostData):
        fieldnames = [f.name for f in fields(PostData)]
    else:
        raise TypeError("PostData is not a dataclass or does not have fields defined.")

    try:
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for post_data_item in post_data_list:
                row_data = post_data_item.__dict__
                writer.writerow(row_data)
        print(f"Successfully wrote {len(post_data_list)} items to '{filepath}'.")
    except Exception as e:
        raise ValueError(f"An error occurred while writing data to '{filepath}': {e}")