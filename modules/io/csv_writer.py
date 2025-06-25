# csv_writer.py
import csv
from typing import List
from dataclasses import fields, is_dataclass
import os

from modules.core.models import PostData

def write_post_data_to_csv(filepath: str, post_data_list: List[PostData]) -> None:
    """Writes a list of ``PostData`` objects to a CSV file."""
    if not post_data_list:
        raise ValueError("No data to write to CSV.")

    # Correctly get field names using the imported 'fields' function and verify PostData is a dataclass.
    if is_dataclass(PostData):
        fieldnames = [f.name for f in fields(PostData)]
    else:
        raise TypeError("PostData is not a dataclass or does not have fields defined.")

    try:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for post_data_item in post_data_list:
                writer.writerow(post_data_item.__dict__)
        print(f"Successfully wrote {len(post_data_list)} items to '{filepath}'.")
    except Exception as e:
        raise ValueError(
            f"An error occurred while writing data to '{filepath}': {e}"
        )


def append_post_data_to_csv(filepath: str, post_data: PostData) -> None:
    """Append a single ``PostData`` entry to ``filepath``.

    The CSV header is written if the file does not already exist.
    """
    if is_dataclass(PostData):
        fieldnames = [f.name for f in fields(PostData)]
    else:
        raise TypeError("PostData is not a dataclass or does not have fields defined.")

    file_exists = os.path.isfile(filepath)

    try:
        with open(filepath, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            writer.writerow(post_data.__dict__)
    except Exception as e:
        raise ValueError(
            f"An error occurred while appending data to '{filepath}': {e}"
        )
