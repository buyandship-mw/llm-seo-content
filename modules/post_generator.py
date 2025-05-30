import json
from typing import Dict, List

from modules.models import DemoData, InputData, PostData
from modules.azure_openai_client import OpenAIClient
from modules.sampler import Sampler

def format_demo_for_category_prompt(demo: DemoData) -> str:
    """Formats a DemoData object for Prompt 1 (Category Prediction) few-shot example."""
    item_details_str = f"""
Item Name: {demo.item_name}
Item Category: {demo.item_category}
"""
    expected_json_output_str = json.dumps({"predicted_category": demo.category}, indent=4)
    return f"{item_details_str}\n\nExpected JSON Output:\n```json\n{expected_json_output_str}\n```"

def format_demo_for_title_content_prompt(demo: DemoData) -> str:
    """Formats a DemoData object for Prompt 2 (Title/Content Gen) few-shot example."""
    item_details_str = f"""Item Details:
Item Name: {demo.item_name}
Item Category: {demo.item_category}
Site: {demo.site}
Warehouse: {demo.warehouse_location}
Region: {demo.region}
Original Item Price: {demo.item_unit_price} {demo.item_unit_price_currency}
Discount: {demo.discount or "N/A"}
Post Category: {demo.category}"""
    expected_json_output_str = json.dumps({"title": demo.title, "content": demo.content}, indent=4)
    return f"{item_details_str}\n\nExpected JSON Output:\n```json\n{expected_json_output_str}\n```"

def predict_post_category(
    input_data: InputData,
    available_categories: List[str],
    ai_client: OpenAIClient,
    sampler: Sampler,
    num_demos: int
) -> str:
    """
    Generates Prompt 1 and calls the AI to predict the post category.
    """
    system_prompt_1 = """You are an expert AI assistant specializing in e-commerce and community engagement. Your task is to analyze item purchase details and select the single most appropriate category for a community post about this item from a given list. Focus on the item's nature, intended use, and common online shopping categorizations. Respond strictly in the specified JSON format."""
    
    if not available_categories:
        print("Warning: No available categories provided. Defaulting category.")
        raise ValueError("Available categories list cannot be empty.")

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
Item Category: {input_data.item_category}

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
    num_demos: int
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
    num_category_demos: int,
    num_content_demos: int
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
    demo_data: List[DemoData] = [
        # US, Electronics
        DemoData(post_id="p1", item_category="Electronics", category="Gadgets", item_name="E-Reader X1 (US)", item_unit_price=129.99, item_unit_price_currency="USD", item_url="url_er_us", site="TechFindsUS", warehouse_id="WH-USW", warehouse_location="US-West", region="US", title="My US E-Reader", content="Content US", like_count=150),
        DemoData(post_id="p2", item_category="Electronics", category="Audio", item_name="Headphones Y2 (US)", item_unit_price=199.50, item_unit_price_currency="USD", item_url="url_hp_us", site="SoundGoodUS", warehouse_id="WH-USE", warehouse_location="US-East", region="US", title="US Quiet Time", content="Music US", like_count=200),
        DemoData(post_id="p4", item_category="Electronics", category="Gadgets", item_name="Thermostat T4 (US)", item_unit_price=99.00, item_unit_price_currency="USD", item_url="url_thermo_us", site="HomeSmartUS", warehouse_id="WH-USW", warehouse_location="US-West", region="US", title="US Smart Home", content="Install US", like_count=180),
        # US, Other Category
        DemoData(post_id="p7", item_category="Home Goods", category="Kitchen", item_name="Coffee Maker (US)", item_unit_price=90.00, item_unit_price_currency="USD", item_url="url_coffee_us", site="KitchenUS", warehouse_id="WH-USC", warehouse_location="US-Central", region="US", title="US Coffee", content="Best brew US", like_count=170),
        # EU, Fashion
        DemoData(post_id="p3", item_category="Fashion", category="Accessories", item_name="Silk Scarf Z3 (EU)", item_unit_price=80.00, item_unit_price_currency="EUR", item_url="url_scarf_eu", site="EuroStyle", warehouse_id="WH-EU-C", warehouse_location="EU-Central", region="EU", title="EU Elegant Scarf", content="Soft EU", like_count=120),
        # EU, Electronics
        DemoData(post_id="p8", item_category="Electronics", category="Gadgets", item_name="E-Reader X1 (EU)", item_unit_price=139.99, item_unit_price_currency="EUR", item_url="url_er_eu", site="TechFindsEU", warehouse_id="WH-EUE", warehouse_location="EU-East", region="EU", title="My EU E-Reader", content="Content EU", like_count=160), # EU version of E-Reader
        # CA, Books
        DemoData(post_id="p5", item_category="Books", category="Fiction", item_name="The Great Novel N5 (CA)", item_unit_price=15.99, item_unit_price_currency="CAD", item_url="url_novel_ca", site="ReadMoreCA", warehouse_id="WH-CA-E", warehouse_location="CA-East", region="CA", title="CA Good Read", content="Page turner CA", like_count=90),
        # CA, Electronics
        DemoData(post_id="p6", item_category="Electronics", category="Computers", item_name="Tablet Pro (CA)", item_unit_price=499.00, item_unit_price_currency="CAD", item_url="url_tab_ca", site="CanTech", warehouse_id="WH-CA-W", warehouse_location="CA-West", region="CA", title="CA New Tablet", content="Fast CA", like_count=250),
        # AU, Other Category (neither Electronics nor Books, for full fallback)
        DemoData(post_id="p9", item_category="Sports", category="Outdoor", item_name="Tent Z1 (AU)", item_unit_price=299.00, item_unit_price_currency="AUD", item_url="url_tent_au", site="AusOutdoor", warehouse_id="WH-AU-S", warehouse_location="AU-Sydney", region="AU", title="AU Camping", content="Great tent AU", like_count=100),
    ]
    sampler_instance = Sampler(all_demo_data=demo_data)

    # 4. Call the main generation function
    print("\nGenerating post data for a US item...")
    try:
        generated_post = generate_post_data_from_input(
            input_data_obj=test_input_data,
            available_categories=_MOCK_AVAILABLE_CATEGORIES,
            ai_client=test_ai_client,
            sampler=sampler_instance,
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
            sampler=sampler_instance,
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