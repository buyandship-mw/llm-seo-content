from typing import Dict, List, Tuple

from modules.models import InputData, PostData
from modules.openai_client import OpenAIClient
from modules.post_generator import generate_post

def process_batch_input_data(
    input_data_list: List[InputData],
    available_categories: List[str],
    warehouses: List[Tuple[str, str]],
    rates: Dict,
    ai_client: OpenAIClient
) -> List[PostData]:
    """
    Processes a list of InputData items and returns a list of PostData items.
    """
    if not available_categories:
        raise ValueError("The 'available_categories' list cannot be empty.")
    if not warehouses:
        raise ValueError("The 'warehouses' list cannot be empty.")

    all_post_data: List[PostData] = []
    for i, input_item in enumerate(input_data_list):
        print(f"Processing item {i + 1}/{len(input_data_list)}: '{input_item.item_url}'...")
        try:
            post_data_result = generate_post(
                client_input=input_item,
                available_bns_categories=available_categories,
                valid_warehouses=warehouses,
                currency_conversion_rates=rates,
                ai_client=ai_client,
                model="gpt-4.1-mini"
            )
            all_post_data.append(post_data_result)
            print(f"Successfully processed item: '{input_item.item_url}'")
        except ValueError as ve:
            print(f"ValueError processing item '{input_item.item_url}': {ve}. Skipping this item.")
        except Exception as e:
            print(f"An unexpected error occurred while processing item '{input_item.item_url}': {e}. Skipping this item.")
            # Optionally, create a PostData object with error details here
            
    return all_post_data