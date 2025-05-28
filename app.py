import os

from modules.azure_openai_client import OpenAIClient # Assuming OpenAIClient (mock or real) is accessible
from modules.csv_parser import load_categories_from_csv, parse_csv_to_input_data
from modules.csv_writer import write_post_data_to_csv
from modules.executor import process_batch_input_data

# --- Configuration ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_FILE = os.path.join(CURRENT_DIR, "data/categories.csv")
INPUT_DATA_FILE = os.path.join(CURRENT_DIR, "data/test.csv")
OUTPUT_POST_DATA_FILE = os.path.join(CURRENT_DIR, "output.csv")

NUM_CATEGORY_DEMOS = 2
NUM_CONTENT_DEMOS = 2

def run_pipeline():
    """Main function to run the post generation pipeline."""
    print("--- Starting Post Generation Pipeline ---")

    # 1. Load data from external sources
    try:
        print(f"Loading categories from: {CATEGORIES_FILE}")
        available_categories = load_categories_from_csv(CATEGORIES_FILE)
        
        print(f"Loading input data from: {INPUT_DATA_FILE}")
        input_items = parse_csv_to_input_data(INPUT_DATA_FILE)
    except Exception as e:
        print(f"Failed to load initial data: {e}")
        return

    if not input_items:
        print("No input data loaded. Exiting pipeline.")
        return
    if not available_categories:
        print("No categories loaded. Exiting pipeline.")
        return

    # 2. Initialize AI Client
    ai_client = OpenAIClient()

    # 3. Process the batch of input data
    print(f"\nProcessing {len(input_items)} items...")
    generated_posts = process_batch_input_data(
        input_data_list=input_items,
        available_categories=available_categories,
        ai_client=ai_client,
        num_category_demos=NUM_CATEGORY_DEMOS,
        num_content_demos=NUM_CONTENT_DEMOS
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