# csv_writer.py
import csv
from typing import List
from dataclasses import fields, is_dataclass

from modules.models import PostData

def write_post_data_to_csv(filepath: str, post_data_list: List[PostData]) -> None:
    """Writes a list of PostData objects to a CSV file."""
    if not post_data_list:
        print("No data to write to CSV.")
        # Optionally, create an empty file with headers if desired
        # This requires PostData to be defined in scope.
        if PostData and is_dataclass(PostData):
            temp_fieldnames = [f.name for f in fields(PostData)]
            try:
                with open(filepath, 'w', encoding='utf-8', newline='') as f_empty:
                    writer_empty = csv.DictWriter(f_empty, fieldnames=temp_fieldnames)
                    writer_empty.writeheader()
                print(f"Wrote empty CSV with headers to '{filepath}'.")
            except Exception as e_empty:
                print(f"Could not write empty CSV with headers: {e_empty}")
        return

    # Correctly get field names using the imported 'fields' function
    # and check if PostData is indeed a dataclass.
    if is_dataclass(PostData): # A more robust check
        fieldnames = [f.name for f in fields(PostData)]
    else: # Fallback if PostData is not a dataclass (e.g., a regular class instance)
        fieldnames = list(post_data_list[0].__dict__.keys())


    try:
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for post_data_item in post_data_list:
                # Convert object to dict for writerow.
                # If PostData is a dataclass, dataclasses.asdict could also be used.
                row_data = post_data_item.__dict__.copy() # Using __dict__ is fine for simple dataclasses
                
                # Handle list fields like 'hashtags' for CSV compatibility
                if 'hashtags' in row_data and isinstance(row_data['hashtags'], list):
                    row_data['hashtags'] = ",".join(row_data['hashtags'])
                
                writer.writerow(row_data)
        print(f"Successfully wrote {len(post_data_list)} items to '{filepath}'.")
    except Exception as e:
        print(f"An error occurred while writing data to '{filepath}': {e}")
        raise