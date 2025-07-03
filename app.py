import os

from modules.clients.openai_client import AzureOpenAIClient, OpenAIClient
from modules.io.csv_parser import (
    load_categories_from_json,
    load_interests_from_json,
    load_warehouses_from_json,
    load_forex_rates_from_json,
    parse_csv_to_post_data,
)

from modules.core.executor import process_batch_input_data

# --- Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_FILE = os.path.join(CURRENT_DIR, "presets/categories.json")
INTERESTS_FILE = os.path.join(CURRENT_DIR, "presets/interests.json")
WAREHOUSES_FILE = os.path.join(CURRENT_DIR, "presets/warehouses.json")
FOREX_RATES_FILE = os.path.join(CURRENT_DIR, "presets/forex_rates.json")
INPUT_DATA_FILE = os.path.join(CURRENT_DIR, "data/test.csv")
OUTPUT_POST_DATA_FILE = os.path.join(CURRENT_DIR, "output.csv")
OUTPUT_IMAGE_FOLDER = os.path.join(CURRENT_DIR, "output_images")
ABORTED_GENERATIONS_FILE = os.path.join(CURRENT_DIR, "aborted.csv")

def run_pipeline():
    """Main function to run the post generation pipeline."""
    print("--- Starting Post Generation Pipeline ---")

    # 1. Load data from external sources
    try:
        print(f"Loading categories from: {CATEGORIES_FILE}")
        available_categories = load_categories_from_json(CATEGORIES_FILE)

        print(f"Loading interests from: {INTERESTS_FILE}")
        interests = load_interests_from_json(INTERESTS_FILE)

        print(f"Loading warehouses from: {WAREHOUSES_FILE}")
        warehouses = load_warehouses_from_json(WAREHOUSES_FILE)

        print(f"Loading forex rates from: {FOREX_RATES_FILE}")
        rates = load_forex_rates_from_json(FOREX_RATES_FILE)

        print(f"Loading input data from: {INPUT_DATA_FILE}")
        input_builders = parse_csv_to_post_data(INPUT_DATA_FILE)
        input_items = [b.build() for b in input_builders]

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
    input_items = input_items[:20]

    # # 3. Process the batch of input data
    print(f"\nProcessing {len(input_items)} items...")
    generated_posts = process_batch_input_data(
        input_data_list=input_items,
        available_categories=available_categories,
        available_interests=interests,
        warehouses=warehouses,
        rates=rates,
        ai_client=ai_client,
        output_filepath=OUTPUT_POST_DATA_FILE,
        image_output_folder=OUTPUT_IMAGE_FOLDER,
        aborted_filepath=ABORTED_GENERATIONS_FILE,
    )

    # 4. Inform user where results are written
    if generated_posts:
        print(
            f"\nAppended {len(generated_posts)} posts to: {OUTPUT_POST_DATA_FILE}"
        )
        print(f"Saved images to folder: {OUTPUT_IMAGE_FOLDER}")
    else:
        print("No posts were generated.")

    print("\n--- Post Generation Pipeline Finished ---")

if __name__ == "__main__":
    run_pipeline()
