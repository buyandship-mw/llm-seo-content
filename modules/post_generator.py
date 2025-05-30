import json
from typing import Dict, List

from modules.models import DemoData, InputData, PostData
from modules.azure_openai_client import OpenAIClient
from modules.sampler import Sampler

def format_demo_for_category_prompt(demo: DemoData) -> str:
    """Formats a DemoData object for Prompt 1 (Category Prediction) few-shot example."""
    item_details_str = f"""Item Details:
Item Name: {demo.item_name}
Item's Own Category: {demo.item_category}
URL Extracted Text: N/A (Demo data does not include this field)
Site: {demo.site}
Region: {demo.region}
Original Price: {demo.item_unit_price} {demo.item_unit_price_currency}"""
    expected_json_output_str = json.dumps({"predicted_category": demo.category}, indent=4)
    return f"{item_details_str}\n\nExpected JSON Output:\n```json\n{expected_json_output_str}\n```"

def format_demo_for_title_content_prompt(demo: DemoData) -> str:
    """Formats a DemoData object for Prompt 2 (Title/Content Gen) few-shot example."""
    item_details_str = f"""Item Details:
Item Name: {demo.item_name}
Item's Own Category: {demo.item_category}
URL Extracted Text: N/A (Demo data does not include this field)
Site: {demo.site}
Warehouse: {demo.warehouse_location}
Region: {demo.region}
Original Item Price: {demo.item_unit_price} {demo.item_unit_price_currency}
Discount: {demo.discount or "N/A"}
Determined Post Category: {demo.category}"""
    expected_json_output_str = json.dumps({"title": demo.title, "content": demo.content}, indent=4)
    return f"{item_details_str}\n\nExpected JSON Output:\n```json\n{expected_json_output_str}\n```"

def predict_post_category(
    input_data: InputData,
    available_categories: List[str],
    ai_client: OpenAIClient,
    sampler: Sampler,
    num_demos: int = 2
) -> str:
    """
    Generates Prompt 1 and calls the AI to predict the post category.
    """
    system_prompt_1 = """You are an expert AI assistant specializing in e-commerce and community engagement. Your task is to analyze item purchase details and select the single most appropriate category for a community post about this item from a given list. Focus on the item's nature, intended use, and common online shopping categorizations. Respond strictly in the specified JSON format."""
    
    if not available_categories:
        print("Warning: No available categories provided. Defaulting category.")
        return "Other"

    formatted_available_categories = "\n".join([f'    "{cat}"' for cat in available_categories])
    
    # Call the imported/module-level retrieve_demos function
    demos = sampler.retrieve_demos(input_data, num_examples=num_demos)
    formatted_demos = "\n\nEXAMPLE:\n".join([format_demo_for_category_prompt(d) for d in demos])
    if formatted_demos: formatted_demos = "EXAMPLE:\n" + formatted_demos

    user_query_1 = f"""Below are details of a purchased item. Please select the MOST appropriate post category for a community discussion about this item from the "Available Post Categories" list.

Available Post Categories:
{formatted_available_categories}

Respond with a JSON object containing a single key "predicted_category" where the value is the name of the selected category string from the list above.

Here are some examples of how items are categorized and the expected JSON output format:
--- BEGIN EXAMPLES ---
{formatted_demos if formatted_demos else "No examples provided."}
--- END EXAMPLES ---

Now, please categorize the following item and provide the output in the specified JSON format:

Item Details:
Item Name: {input_data.item_name}
Item's Own Category: {input_data.item_category}
URL Extracted Text: {input_data.url_extracted_text or "N/A"}
Site: {input_data.site}
Region: {input_data.region}
Original Price: {input_data.item_unit_price} {input_data.item_unit_price_currency}

Expected JSON Output:"""

    raw_json_response = ai_client.get_completion(system_prompt_1, user_query_1)
    try:
        clean_json_response = raw_json_response.strip().removeprefix("```json").removesuffix("```").strip()
        if not clean_json_response: raise json.JSONDecodeError("Cleaned JSON response is empty", clean_json_response, 0)
        category_data = json.loads(clean_json_response)
        predicted_cat = category_data["predicted_category"]
        if predicted_cat not in available_categories:
            print(f"Warning: LLM predicted category '{predicted_cat}' not in available list. Using first available category.")
            return available_categories[0]
        return predicted_cat
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing category JSON response: {e}\nRaw response was: '{raw_json_response}'")
        return available_categories[0]


def generate_title_and_content(
    input_data: InputData,
    predicted_category: str,
    ai_client: OpenAIClient,
    sampler: Sampler,
    num_demos: int = 2
) -> Dict[str, str]:
    """
    Generates Prompt 2 and calls the AI to generate title and content.
    """
    system_prompt_2 = f"""You are a creative and engaging AI copywriter specializing in crafting community posts for an e-commerce platform. Your goal is to generate an enthusiastic and informative post title and content based on the provided item details and post category.

IMPORTANT INSTRUCTIONS:
1.  **Regional Adaptation:** Tailor the language, tone, and style to the specified `region` ('{input_data.region}'). For example, use colloquial Cantonese-style Chinese for 'HK', Taiwanese Mandarin for 'TW', etc.
2.  **Currency Presentation:** Clearly state the original purchase price as '{input_data.item_unit_price} {input_data.item_unit_price_currency}'. Make this sound natural. Do NOT attempt to convert this price.
3.  **Item Details:** Weave in information from `item_name` ('{input_data.item_name}'), and `url_extracted_text` (if provided: '{input_data.url_extracted_text or "N/A"}').
4.  **Purchase Context:** Mention `site` ('{input_data.site}') and `warehouse_location` ('{input_data.warehouse_location}').
5.  **Tone:** Enthusiastic, helpful, like a real person.
7.  **Value:** If `discount` ('{input_data.discount or "No discount"}') is mentioned and not null/empty, highlight it.
8.  Do NOT invent new product features.
9.  The post is for the '{predicted_category}' category.
10. **Respond with a JSON object containing two keys: "title" (string) and "content" (string). Ensure content is a single string, possibly with newlines (\\n).**
"""
    # Call the imported/module-level retrieve_demos function
    demos = sampler.retrieve_demos(input_data, num_examples=num_demos)
    formatted_demos = "\n\nEXAMPLE:\n".join([format_demo_for_title_content_prompt(d) for d in demos])
    if formatted_demos: formatted_demos = "EXAMPLE:\n" + formatted_demos
        
    user_query_2 = f"""Generate an engaging community post (Title and Content) for the following item purchase. Respond in the specified JSON format.

Here are some examples of great community posts and their JSON output format:
--- BEGIN EXAMPLES ---
{formatted_demos if formatted_demos else "No examples provided."}
--- END EXAMPLES ---

Now, generate a Title and Content for the following item. Provide the output in the specified JSON format:

Item Details:
Item Name: {input_data.item_name}
Item's Own Category: {input_data.item_category}
URL Extracted Text: {input_data.url_extracted_text or "N/A"}
Site: {input_data.site}
Warehouse Location: {input_data.warehouse_location}
Warehouse ID: {input_data.warehouse_id}
Region: {input_data.region}
Original Item Price: {input_data.item_unit_price} {input_data.item_unit_price_currency}
Discount: {input_data.discount or "N/A"}
Payment Method: {input_data.payment_method or "N/A"}
Item Weight: {input_data.item_weight or "N/A"}
Determined Post Category: {predicted_category}

Expected JSON Output:"""

    raw_json_response = ai_client.get_completion(system_prompt_2, user_query_2)
    try:
        clean_json_response = raw_json_response.strip().removeprefix("```json").removesuffix("```").strip()
        if not clean_json_response: raise json.JSONDecodeError("Cleaned JSON response is empty", clean_json_response, 0)
        title_content_data = json.loads(clean_json_response)
        if "title" in title_content_data and "content" in title_content_data:
            return title_content_data
        else:
            raise KeyError("Missing 'title' or 'content' in JSON response.")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing title/content JSON response: {e}\nRaw response was: '{raw_json_response}'")
        return {"title": "Error: Could not generate title", "content": f"Error: Could not generate content. Raw LLM output was: {raw_json_response}"}

# --- Main Orchestration Function ---

def generate_post_data_from_input(
    input_data_obj: InputData,
    available_categories: List[str],
    ai_client: OpenAIClient,
    sampler: Sampler,
    num_category_demos: int = 2,
    num_content_demos: int = 2
) -> PostData:
    """
    Orchestrates the generation of a PostData object from an InputData object.
    The list of available categories must be loaded by the caller and passed in.
    The retrieve_demos function is imported from the 'sampler' module.
    """
    if not available_categories:
        # This check is important. The caller is responsible for providing a valid list.
        raise ValueError("Available categories list cannot be empty.")

    # The SamplerModule instance is no longer passed; retrieve_demos is called directly.
    llm_predicted_post_category = predict_post_category(
        input_data_obj, available_categories, ai_client, sampler, num_demos=num_category_demos
    )
    
    llm_generated_title_content = generate_title_and_content(
        input_data_obj, llm_predicted_post_category, ai_client, sampler, num_demos=num_content_demos
    )
    
    post_data_instance = PostData(
        item_category=input_data_obj.item_category,
        category=llm_predicted_post_category,
        item_name=input_data_obj.item_name,
        item_unit_price=input_data_obj.item_unit_price,
        item_unit_price_currency=input_data_obj.item_unit_price_currency,
        item_url=input_data_obj.item_url,
        site=input_data_obj.site,
        warehouse_id=input_data_obj.warehouse_id,
        warehouse_location=input_data_obj.warehouse_location,
        region=input_data_obj.region,
        title=llm_generated_title_content.get("title", "Error: Title not found"),
        content=llm_generated_title_content.get("content", "Error: Content not found"),
        discount=input_data_obj.discount if isinstance(input_data_obj.discount, (float, str, type(None))) else str(input_data_obj.discount),
        payment_method=input_data_obj.payment_method,
        item_weight=input_data_obj.item_weight if isinstance(input_data_obj.item_weight, (float, str, type(None))) else str(input_data_obj.item_weight),
    )
    
    return post_data_instance

if __name__ == "__main__":
    print("--- Running Post Generator Test ---")

    # 1. Define sample available categories (as it's now an input to the main function)
    #    This list will also be used by the mock OpenAIClient via the global.
    _MOCK_AVAILABLE_CATEGORIES = ["Electronics & Gadgets", "Storage Solutions", "Computer Components", "Gaming Gear", "Other"]
    
    # 2. Create sample InputData
    sample_input_data_dict = {
        "item_category": "Electronics Component",
        "discount": "15%",
        "item_name": "SuperFast NVMe SSD 2TB",
        "item_unit_price": 199.99,
        "item_unit_price_currency": "USD",
        "item_url": "http://example.com/ssd2tb",
        "payment_method": "Credit Card",
        "site": "SuperTechStore.com",
        "warehouse_id": "WH-US-CA-01", # Added warehouse_id
        "warehouse_location": "California Main Warehouse", # Renamed from 'warehouse'
        "item_weight": "0.2 kg",
        "region": "US",
        "url_extracted_text": "Blazing fast speeds with new controller, 2TB capacity for all your games and files."
    }
    test_input_data = InputData(**sample_input_data_dict)

    # 3. Instantiate mock OpenAIClient
    test_ai_client = OpenAIClient()

    # 4. Call the main generation function
    print("\nGenerating post data for a US item...")
    try:
        generated_post = generate_post_data_from_input(
            input_data_obj=test_input_data,
            available_categories=_MOCK_AVAILABLE_CATEGORIES,
            ai_client=test_ai_client,
            num_category_demos=1, # Using 1 demo for quicker test run
            num_content_demos=1
        )

        # 5. Print results
        print("\n--- Generated PostData ---")
        print(f"Region: {generated_post.region}")
        print(f"Item Name: {generated_post.item_name}")
        print(f"Post Category: {generated_post.category}")
        print(f"Title: {generated_post.title}")
        print(f"Content: {generated_post.content}")
        print("--------------------------\n")

    except Exception as e:
        print(f"An error occurred during test generation: {e}")
        import traceback
        traceback.print_exc()

    # Test with a different region (e.g., HK)
    sample_input_data_hk_dict = {
        "item_category": "Fashion Accessory",
        "discount": None,
        "item_name": "Designer Silk Scarf - Sakura Edition",
        "item_unit_price": 8500.00, # Example price in JPY
        "item_unit_price_currency": "JPY",
        "item_url": "http://example.jp/scarf-sakura",
        "payment_method": "PayPal",
        "site": "TokyoBoutique.jp",
        "warehouse_id": "WH-JP-TYO-S2",
        "warehouse_location": "Tokyo Sakura Warehouse",
        "item_weight": "0.1 kg",
        "region": "HK", # Target region for the post
        "url_extracted_text": "Limited edition 100% silk scarf with beautiful sakura cherry blossom designs. Hand-rolled edges."
    }
    test_input_data_hk = InputData(**sample_input_data_hk_dict)
    
    print("\nGenerating post data for an HK item (bought in JPY)...")
    try:
        generated_post_hk = generate_post_data_from_input(
            input_data_obj=test_input_data_hk,
            available_categories=_MOCK_AVAILABLE_CATEGORIES, # Using the same list for test
            ai_client=test_ai_client,
            num_category_demos=1,
            num_content_demos=1
        )
        print("\n--- Generated PostData (HK) ---")
        print(f"Region: {generated_post_hk.region}")
        print(f"Item Name: {generated_post_hk.item_name}")
        print(f"Post Category: {generated_post_hk.category}")
        print(f"Title: {generated_post_hk.title}")
        print(f"Content: {generated_post_hk.content}")
        print("--------------------------\n")
    except Exception as e:
        print(f"An error occurred during HK test generation: {e}")
        import traceback
        traceback.print_exc()

    print("--- Test Run Complete ---")