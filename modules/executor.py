from typing import List

from modules.models import InputData, PostData
from modules.openai_client import AzureOpenAIClient
from modules.post_generator import compile_post_data
from modules.sampler import Sampler

def process_batch_input_data(
    input_data_list: List[InputData],
    available_categories: List[str],
    ai_client,
    sampler: Sampler,
    num_category_demos: int
) -> List[PostData]:
    """
    Processes a list of InputData items and returns a list of PostData items.
    """
    if not available_categories:
        raise ValueError("The 'available_categories' list cannot be empty.")

    all_post_data: List[PostData] = []
    for i, input_item in enumerate(input_data_list):
        print(f"Processing item {i + 1}/{len(input_data_list)}: '{input_item.item_name}'...")
        try:
            post_data_result = compile_post_data(
                input_data_obj=input_item,
                available_categories=available_categories,
                ai_client=ai_client,
                sampler=sampler,
                num_category_demos=num_category_demos
            )
            all_post_data.append(post_data_result)
            print(f"Successfully processed item: '{input_item.item_name}'")
        except ValueError as ve:
            print(f"ValueError processing item '{input_item.item_name}': {ve}. Skipping this item.")
        except Exception as e:
            print(f"An unexpected error occurred while processing item '{input_item.item_name}': {e}. Skipping this item.")
            # Optionally, create a PostData object with error details here
            
    return all_post_data