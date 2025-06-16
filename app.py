import os

from modules.openai_client import AzureOpenAIClient, OpenAIClient
from modules.csv_parser import load_categories_from_csv, load_warehouses_from_csv, parse_csv_to_post_data
from modules.csv_writer import write_post_data_to_csv
from modules.executor import process_batch_input_data

# --- Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_FILE = os.path.join(CURRENT_DIR, "data/categories.csv")
WAREHOUSES_FILE = os.path.join(CURRENT_DIR, "data/warehouses.csv")
INPUT_DATA_FILE = os.path.join(CURRENT_DIR, "data/test.csv")
OUTPUT_POST_DATA_FILE = os.path.join(CURRENT_DIR, "output.csv")

rates = {
    "USD": {"GBP": 0.80, "EUR": 0.92, "HKD": 7.80, "JPY": 143.26},
    "GBP": {"USD": 1.25, "EUR": 1.15, "HKD": 9.75, "JPY": 194.42},
    "EUR": {"USD": 1.08, "GBP": 0.87, "HKD": 8.45, "JPY": 163.61},
    "HKD": {"USD": 0.13, "GBP": 0.10, "EUR": 0.12, "JPY": 18.26},
}

def run_pipeline():
    """Main function to run the post generation pipeline."""
    print("--- Starting Post Generation Pipeline ---")

    # 1. Load data from external sources
    try:
        print(f"Loading categories from: {CATEGORIES_FILE}")
        available_categories = load_categories_from_csv(CATEGORIES_FILE)

        print(f"Loading warehouses from: {WAREHOUSES_FILE}")
        warehouses = load_warehouses_from_csv(WAREHOUSES_FILE)
        print(warehouses)
        
        print(f"Loading input data from: {INPUT_DATA_FILE}")
        input_items = parse_csv_to_post_data(INPUT_DATA_FILE)

    except Exception as e:
        print(f"Failed to load initial data or initialize sampler: {e}")
        return

    if not input_items:
        print("No input data loaded. Exiting pipeline.")
        return
    if not available_categories:
        print("No categories loaded. Exiting pipeline.")
        return

    # 2. Initialize AI Client
    ai_client = OpenAIClient()
    input_items = input_items[5:6]

    # # 3. Process the batch of input data
    print(f"\nProcessing {len(input_items)} items...")
    generated_posts = process_batch_input_data(
        input_data_list=input_items,
        available_categories=available_categories,
        warehouses=warehouses,
        rates=rates,
        ai_client=ai_client
    )

    # 4. Write results to an output file
    if generated_posts:
        print(f"\nWriting {len(generated_posts)} generated posts to: {OUTPUT_POST_DATA_FILE}")
        try:
            write_post_data_to_csv(OUTPUT_POST_DATA_FILE, generated_posts)
        except Exception as e:
            print(f"Failed to write output data: {e}")
    else:
        print("No posts were generated.")

    print("\n--- Post Generation Pipeline Finished ---")

if __name__ == "__main__":
    run_pipeline()