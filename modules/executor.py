from typing import Dict, List

from dataclasses import asdict
from modules.models import PostData, Category, Warehouse, Interest
from modules.openai_client import OpenAIClient
from modules.post_generator import generate_post
from modules.scraper import extract_product_data
from modules.post_data_builder import PostDataBuilder
from modules.csv_writer import append_post_data_to_csv
from utils.image_processing import save_image_from_url

def process_batch_input_data(
    input_data_list: List[PostData],
    available_categories: List[Category],
    available_interests: List[Interest],
    warehouses: List[Warehouse],
    rates: Dict,
    ai_client: OpenAIClient,
    output_filepath: str | None = None,
    image_output_folder: str | None = None,
) -> List[PostData]:
    """
    Processes a list of ``PostData`` items and returns a list of results.

    If ``image_output_folder`` is provided, each post's ``image_url`` is
    downloaded and padded to a square image saved in that folder. The local
    path is stored on the ``PostData`` instance as ``local_image_path``.
    """
    if not available_categories:
        raise ValueError("The 'available_categories' list cannot be empty.")
    if not available_interests:
        raise ValueError("The 'available_interests' list cannot be empty.")
    if not warehouses:
        raise ValueError("The 'warehouses' list cannot be empty.")

    all_post_data: List[PostData] = []
    for i, input_item in enumerate(input_data_list):
        print(f"Processing item {i + 1}/{len(input_data_list)}: '{input_item.item_url}'...")
        # --- Scrape additional data before invoking the LLM ---
        enriched_input = input_item
        try:
            scraped = extract_product_data(url=input_item.item_url)
            print(f"Scraped data for {input_item.item_url}: {scraped}")
            builder = PostDataBuilder.from_dict(asdict(input_item))
            builder.update_from_dict(scraped)
            enriched_input = builder.build()
        except Exception as scrape_err:
            print(f"Warning: Scraper failed for {input_item.item_url}: {scrape_err}. Using original input.")

        try:
            post_data_result = generate_post(
                item_data=enriched_input,
                available_bns_categories=available_categories,
                available_interests=available_interests,
                valid_warehouses=warehouses,
                currency_conversion_rates=rates,
                ai_client=ai_client,
                model="gpt-4.1-mini"
            )
            if image_output_folder and post_data_result.image_url:
                try:
                    local_path = save_image_from_url(
                        post_data_result.image_url, image_output_folder
                    )
                    setattr(post_data_result, "local_image_path", local_path)
                except Exception as img_err:
                    print(f"Error processing {post_data_result.image_url}: {img_err}")
            all_post_data.append(post_data_result)
            if output_filepath:
                try:
                    append_post_data_to_csv(output_filepath, post_data_result)
                except Exception as write_err:
                    print(
                        f"Failed to append result for {input_item.item_url} to '{output_filepath}': {write_err}"
                    )
            print(f"Successfully processed item: '{input_item.item_url}'")
        except ValueError as ve:
            print(f"ValueError processing item '{input_item.item_url}': {ve}. Skipping this item.")
        except Exception as e:
            print(f"An unexpected error occurred while processing item '{input_item.item_url}': {e}. Skipping this item.")
            # Optionally, create a PostData object with error details here
            
    return all_post_data
