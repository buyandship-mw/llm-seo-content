# modules/post_generator.py

import json
from typing import Dict, List, Optional, Union, Any

# Assuming these models and clients are defined in your 'modules' directory
from modules.models import DemoData, InputData, PostData
from modules.openai_client import OpenAIClient, extract_and_parse_json # Using your client
from modules.sampler import Sampler

# --- Master Post Examples ---
# Craft one high-quality example post for each region.
# The LLM will use this as a strong guide for structure, tone, and style.

# Just HK region for now
MASTER_POST_EXAMPLES = {
    "HK": {
        "item_name": "【尋寶區】日本 Fujifilm Instax Mini 12 即影即有相機 (Lilac Purple 紫色)",
        "warehouse_location": "Ibaraki",
        "title": "日本 Fujifilm Instax Mini 12 (Lilac Purple 紫色)",
        "content":
"""
📸 Fujifilm Instax Mini 12（Lilac Purple 紫色）
- 得意設計＋超易用
- 自動曝光，唔使調光
- 自拍模式＋自拍鏡
- 約 5 秒即印，即影即分享
- 紫色款，打卡又靚又有型

💬 用家評價
👍 易用、靚設計，新手啱用
⚠️ 強光下會過曝，要小心使用

🚚 點解經 BNS 買？
📦 按實重收費，運費清晰
🧳 免費合倉，慳運費
📍 實時追蹤＋彈性派送

🛍️ 即刻經 BNS 落單，將呢部靚相機帶返屋企，影低每個開心moment！
""",
        "product_image_url": "http://example.com/images/sample_product_hk.jpg"
    }
}

def format_demo_for_category_prompt(demo: DemoData) -> str:
    # This function remains unchanged as it's for category prediction examples.
    item_details_str = f"""Item Details:
Item Name: {demo.item_name}
Item's Own Category: {demo.item_category}
"""
    expected_json_output_str = json.dumps({"predicted_category": demo.category}, indent=4, ensure_ascii=False)
    return f"{item_details_str}\n\nExpected JSON Output:\n```json\n{expected_json_output_str}\n```"

def predict_post_category(
    input_data: InputData,
    available_categories: List[str],
    ai_client: OpenAIClient,
    sampler: Optional[Sampler], # Sampler is now optional for this module overall
    num_demos: int,
    model_name: str = "gpt-4.1-mini"
) -> str:
    if not available_categories:
        print("Error: No available categories provided for prediction.")
        raise ValueError("The 'available_categories' list cannot be empty.")
    
    # This function can still use the sampler if DemoData for categories exists.
    system_prompt_1 = """You are an expert AI assistant specializing in e-commerce. Your task is to analyze item details and select the single most appropriate category for a community post about this item from the given list. Respond strictly in the specified JSON format: {"predicted_category": "Chosen Category Name"}."""

    formatted_available_categories = "[\n" + ",\n".join([f'    "{cat}"' for cat in available_categories]) + "\n]"
    
    formatted_demos_str = ""
    if sampler and num_demos > 0:
        demos = sampler.retrieve_demos(input_data, num_examples=num_demos)
        if demos:
            formatted_demos_str = "\n\n---\nEXAMPLE:\n".join([format_demo_for_category_prompt(d) for d in demos])
            formatted_demos_str = "EXAMPLE:\n" + formatted_demos_str
    
    user_prompt_content = f"""Analyze the item details below and select the MOST appropriate post category from the "Available Post Categories" list.

Available Post Categories:
{formatted_available_categories}

{formatted_demos_str if formatted_demos_str else "No examples provided for category context."}

---
Item to categorize:

Item Name: {input_data.item_name}
Item's Own Category: {input_data.item_category}
URL Extracted Text: {input_data.url_extracted_text or "N/A"}

Based on these details, what is the single most appropriate post category?
Respond strictly with a JSON object: {{"predicted_category": "<selected post category>"}}

Expected JSON Output:"""

    messages = [
        {"role": "system", "content": system_prompt_1},
        {"role": "user", "content": user_prompt_content}
    ]
    
    raw_json_string = ai_client.get_completion( 
        model=model_name, 
        messages=messages
    )

    default_category = available_categories[0] if available_categories else "Other"

    if not raw_json_string:
        print(f"Error: No response from AI for category prediction of '{input_data.item_name}'. Defaulting to '{default_category}'.")
        return default_category
        
    try:
        category_data = extract_and_parse_json(raw_json_string)
        
        if not isinstance(category_data, dict):
            print(f"Error: Parsed JSON for category is not a dictionary for '{input_data.item_name}'. Raw response: '{raw_json_string}'. Defaulting to '{default_category}'.")
            return default_category

        predicted_cat = category_data.get("predicted_category")

        if not predicted_cat or not isinstance(predicted_cat, str) or (available_categories and predicted_cat not in available_categories):
            if available_categories:
                 print(f"Warning: LLM predicted category '{predicted_cat}' is invalid, not a string, or not in available list. Raw response: '{raw_json_string}'. Defaulting to '{default_category}'.")
            else:
                 print(f"Warning: LLM predicted category '{predicted_cat}' is invalid or not a string. Raw response: '{raw_json_string}'. Defaulting to '{default_category}'.")
            return default_category
        return predicted_cat
    except json.JSONDecodeError as e:
        print(f"Error parsing category JSON response for '{input_data.item_name}': {e}\nRaw response was: '{raw_json_string}'. Defaulting to '{default_category}'.")
        return default_category
    except TypeError as e: 
        print(f"Type error processing parsed category JSON for '{input_data.item_name}': {e}\nRaw response was: '{raw_json_string}'. Defaulting to '{default_category}'.")
        return default_category

def generate_post_body(
    input_data: InputData,
    predicted_post_category: str, # For context, if LLM needs it
    ai_client: OpenAIClient,
    model_name: str = "gpt-4.1-mini" # Or your preferred model like gpt-4-turbo
) -> Dict[str, Any]:
    
    region_key = input_data.region.upper()
    master_example = MASTER_POST_EXAMPLES.get(region_key)
    if not master_example:
        print(f"Warning: No master example found for region '{input_data.region}'. Using EN example as fallback.")
        master_example = MASTER_POST_EXAMPLES.get("EN")
        if not master_example: # Should not happen if EN is defined
             print(f"Critical Error: Default EN master example not found. Cannot generate post body.")
             return {
                "title": f"{input_data.item_name} - Content Generation Error",
                "product_image_url": None,
                "content": "Error: Master example configuration missing."
            }

    example_json_str = json.dumps({
        "item_name": master_example["item_name"],
        "warehouse_location": master_example["warehouse_location"],
        "title": master_example["title"],
        "content": master_example["content"],
        "product_image_url": master_example["product_image_url"]
    }, indent=4, ensure_ascii=False)

    system_prompt_content = f"""You are an Expert Recommender and Content Curator for BNS, a global package forwarding service. Your primary goal is to create informative, appealing, and mobile-first marketplace-style posts.

You will be provided with an EXAMPLE POST for the target region: '{input_data.region}'.
Your task is to:
1.  Thoroughly analyze the NEW item details provided below.
2.  **Search the internet to gather fresh and relevant information** about this NEW item (features, benefits, user reviews) and to **find a publicly accessible URL for a high-quality product image of the NEW item**.
3.  **Follow the structure, tone, language, and style of the provided EXAMPLE POST** to generate a new post for the NEW item.
4.  Specifically:
    a.  Generate a `title` for the NEW item that matches the style of the example title, translated appropriately for the region, and incorporating the NEW item's name.
    b.  Generate `content` for the NEW item. This content must have three sections, with headings styled like the example.
        - The content for each section (Product Intro, User Reviews, Why BNS) must be about the NEW item, based on your web search.
        - Ensure mobile-first readability (short paragraphs, scannability, bullet points for lists).
5.  Your entire response MUST be a single, valid JSON object with exactly three keys: "title", "content", and "product_image_url" (or `null` if not found).
"""

    user_prompt_for_item = f"""Here is the MASTER EXAMPLE POST for region '{input_data.region}'.
Use this example as a template for structure, tone, and style.
The content within this example (features, review details, etc.) is illustrative for its own placeholder item.
You must generate NEW content specific to the 'Item Details for Processing' provided below, based on your web search for THAT item.

MASTER EXAMPLE POST (Region: {input_data.region}):
```json
{example_json_str}
```

---
Now, generate the expert recommender post for the following NEW item.
Remember to:
- **Search the internet comprehensively** for the NEW item: '{input_data.item_name}'.
- **Strictly follow the JSON output format** and the structure/style of the master example.
- **Replace placeholders** like '{{{{ITEM_NAME}}}}' and '{{{{WAREHOUSE_LOCATION}}}}' in your generated content with the NEW item's specific details.
- **Tailor all text** (title, headers, body) to the NEW item, in the language and style of the region '{input_data.region}'.

Item Details for Processing (NEW ITEM):
- Product Name: {input_data.item_name}
- Item's Own Category (for context): {input_data.item_category}
- Item URL (for context and as a search starting point): {input_data.item_url}
- URL Extracted Text (initial info, if available): {input_data.url_extracted_text or 'N/A'}
- Image URL (from input, for visual context if model is vision-capable, if available): {input_data.image_url or 'N/A'}
- Target Region for this Post: {input_data.region}
- BNS Warehouse Location (Origin for "Why BNS" section): {input_data.warehouse_location}
- Discount (if any, mention if significant): {input_data.discount or 'N/A'}
- Post Category (overall BNS post category): {predicted_post_category}

Expected JSON Output (for the NEW ITEM '{input_data.item_name}'):"""
    
    messages_for_llm = [{"role": "system", "content": system_prompt_content}]
    
    user_content_payload: Union[str, List[Dict[str, Any]]] = user_prompt_for_item
    if input_data.image_url and (input_data.image_url.startswith("http://") or input_data.image_url.startswith("https://")):
        current_user_content_list = [{"type": "text", "text": user_prompt_for_item}]
        current_user_content_list.append({"type": "image_url", "image_url": {"url": input_data.image_url, "detail": "auto"}})
        user_content_payload = current_user_content_list
        print(f"Info: Sending image URL {input_data.image_url} to vision-capable model for item '{input_data.item_name}'.")
    
    messages_for_llm.append({"role": "user", "content": user_content_payload})

    raw_json_string = ai_client.get_completion_with_search(
        model=model_name,
        messages=messages_for_llm
    )

    default_error_response = {
        "title": f"{input_data.item_name} - Content Generation Error",
        "product_image_url": None,
        "content": f"## Error: Content Generation Failed\nDetails unavailable for {input_data.item_name}.\n\n## Error\nUser review summary unavailable.\n\n## Error\nBNS benefits for item from {input_data.warehouse_location} could not be generated."
    }

    if not raw_json_string:
        print(f"Error: No response from AI for post body generation of '{input_data.item_name}'.")
        return default_error_response
        
    try:
        parsed_data = extract_and_parse_json(raw_json_string)
        
        if not isinstance(parsed_data, dict):
            print(f"Error: Parsed JSON for post body is not a dictionary for '{input_data.item_name}'. Raw: '{raw_json_string}'.")
            return default_error_response

        final_title_raw = parsed_data.get("title")
        final_content_raw = parsed_data.get("content")
        product_image_url_raw = parsed_data.get("product_image_url")

        if isinstance(final_title_raw, str) and final_title_raw.strip():
            final_title = final_title_raw.strip()
        else:
            print(f"Warning: 'title' from LLM is invalid or empty for '{input_data.item_name}'. Using item name. Raw: '{raw_json_string}'.")
            final_title = input_data.item_name

        if isinstance(final_content_raw, str) and final_content_raw.strip():
            final_content = final_content_raw.strip()
        else:
            print(f"Warning: 'content' from LLM is invalid or empty for '{input_data.item_name}'. Using error content. Raw: '{raw_json_string}'.")
            final_content = f"## Content Error for {final_title}\nCould not generate product details.\n\n## User Feedback Error\nCould not generate user feedback summary.\n\n## BNS Information Error\nCould not generate BNS advantages."
        
        product_image_url: Optional[str] = None
        if isinstance(product_image_url_raw, str) and product_image_url_raw.strip():
            if product_image_url_raw.startswith("http://") or product_image_url_raw.startswith("https://"):
                product_image_url = product_image_url_raw
            else:
                print(f"Warning: 'product_image_url' ('{product_image_url_raw}') is not valid URL. Setting to None. Raw: '{raw_json_string}'.")
        elif product_image_url_raw is not None:
            print(f"Warning: 'product_image_url' is not string or null. Setting to None. Raw: '{raw_json_string}'.")

        return {"title": final_title, "content": final_content, "product_image_url": product_image_url}

    except json.JSONDecodeError as e:
        print(f"Error parsing post body JSON for '{input_data.item_name}': {e}\nRaw: '{raw_json_string}'.")
        return default_error_response
    except Exception as e: 
        print(f"Unexpected error processing post body JSON for '{input_data.item_name}': {e}\nRaw: '{raw_json_string}'.")
        return default_error_response


def compile_post_data(
    input_data_obj: InputData,
    available_categories: List[str],
    ai_client: OpenAIClient, 
    sampler: Optional[Sampler], # Sampler is now optional, primarily for category prediction
    num_category_demos: int = 1, # For category prediction
    # num_content_demos is removed as it's not used by generate_post_body anymore
    category_model_name: str = "gpt-4.1-mini",
    content_model_name: str = "gpt-4.1-mini" # Recommend a strong model for this task
) -> PostData:
    print(f"\n--- Compiling Post Data for: {input_data_obj.item_name} (Region: {input_data_obj.region}) ---")

    llm_predicted_post_category = predict_post_category(
        input_data_obj, available_categories, ai_client, sampler, 
        num_demos=num_category_demos, model_name=category_model_name
    )
    print(f"Predicted Post Category for '{input_data_obj.item_name}': {llm_predicted_post_category}")
    
    post_body_elements = generate_post_body( # No sampler or num_demos here
        input_data_obj, 
        llm_predicted_post_category, 
        ai_client, 
        model_name=content_model_name
    )
    generated_title = post_body_elements.get("title")
    generated_content = post_body_elements.get("content")
    generated_image_url = post_body_elements.get("product_image_url")

    print(f"Generated Title for '{input_data_obj.item_name}': {generated_title}")
    if generated_image_url:
        print(f"Generated Product Image URL: {generated_image_url}")
    else:
        print(f"No Product Image URL generated for '{input_data_obj.item_name}'.")
    
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
        title=generated_title,
        content=generated_content,
        product_image_url=generated_image_url,
        discount=input_data_obj.discount,
        payment_method=input_data_obj.payment_method,
        item_weight=input_data_obj.item_weight,
    )
    
    return post_data_instance

# --- Test Execution Block ---
if __name__ == "__main__":
    print("--- Running Post Generator Test (Single Master Example Strategy) ---")

    _MOCK_AVAILABLE_CATEGORIES_FOR_TEST = ["Electronics & Gadgets", "Fashion & Apparel", "Home Goods", "Books", "Travel Gear", "Beauty & Health", "Other"]
    
    sample_input_data_list = [
        InputData(**{
            "item_category": "Electronics", "discount": "10%", "item_name": "NovaBook Pro 15 Laptop (2024)",
            "item_unit_price": 1299.99, "item_unit_price_currency": "USD", "item_url": "http://example.com/novabookpro",
            "payment_method": "Visa", "site": "TechSprout.com", "warehouse_id": "WH-US-W",
            "warehouse_location": "US-West Coast Hub", "item_weight": "1.8 kg", "region": "US",
            "url_extracted_text": "The latest NovaBook Pro 15 features the new M3X chip, a stunning liquid retina display, and up to 20 hours of battery life. Perfect for professionals on the go.",
            "image_url": "http://example.com/images/novabook.jpg" 
        }),
        InputData(**{
            "item_category": "Travel Accessory", "discount": None, "item_name": "SkySailor Carry-On Suitcase",
            "item_unit_price": 150.00, "item_unit_price_currency": "EUR", "item_url": "http://example.com/skysailor",
            "payment_method": "PayPal", "site": "EuroTravelGoods.com", "warehouse_id": "WH-EU-FR",
            "warehouse_location": "Paris Logistics Center (France)", "item_weight": "2.5 kg", "region": "HK", # Test HK
            "url_extracted_text": "Ultra-lightweight and durable carry-on, compliant with most airlines. Features 360-degree spinner wheels and a built-in TSA lock.",
            "image_url": None
        }),
         InputData(**{
            "item_category": "Beauty", "discount": "5%", "item_name": "Sakura Bloom Face Cream",
            "item_unit_price": 750.00, "item_unit_price_currency": "TWD", "item_url": "http://example.com/sakuracream",
            "payment_method": "Credit Card", "site": "TWBeautyFinds.com", "warehouse_id": "WH-TW",
            "warehouse_location": "Taoyuan Logistics (Taiwan)", "item_weight": "0.2 kg", "region": "TW", # Test TW
            "url_extracted_text": "Rich moisturizing cream with sakura extract for radiant skin. Suitable for all skin types.",
            "image_url": "https://example.com/images/sakura_face_cream.jpg"
        }),
    ]
    
    # Sampler is now only needed if predict_post_category uses demos.
    # If predict_post_category also moves to zero-shot or a different example strategy,
    # sampler_instance might become None or not initialized.
    # For now, we assume it might still be used for category prediction demos.
    sample_demo_data_for_category_sampler: List[DemoData] = [
        DemoData(post_id="cat_demo1", item_category="Electronics", category="Laptops", item_name="Demo Laptop", region="US", item_unit_price=0, item_unit_price_currency="", item_url="", site="", warehouse_id="", warehouse_location="", title="", content="", like_count=0),
        DemoData(post_id="cat_demo2", item_category="Travel", category="Luggage", item_name="Demo Suitcase", region="HK",item_unit_price=0, item_unit_price_currency="", item_url="", site="", warehouse_id="", warehouse_location="", title="", content="", like_count=0),
    ]
    
    try:
        test_ai_client = OpenAIClient(config_file='config.ini') 
    except Exception as e:
        print(f"Could not initialize OpenAIClient: {e}. Ensure config.ini is set up or mock client.")
        exit()

    # Initialize sampler if you have demo data for category prediction
    # If not, sampler_instance can be None, and predict_post_category should handle it.
    category_sampler_instance: Optional[Sampler] = None
    if sample_demo_data_for_category_sampler:
        category_sampler_instance = Sampler(all_demo_data=sample_demo_data_for_category_sampler)
    else:
        print("Info: No demo data provided for category sampler. Category prediction will be zero-shot or rely on general model knowledge.")


    print(f"\n--- Running pipeline for {len(sample_input_data_list)} items ---")
    for test_input_obj in sample_input_data_list:
        try:
            generated_post_obj = compile_post_data(
                input_data_obj=test_input_obj,
                available_categories=_MOCK_AVAILABLE_CATEGORIES_FOR_TEST,
                ai_client=test_ai_client,
                sampler=category_sampler_instance, # Pass sampler for category prediction
                num_category_demos=1 if category_sampler_instance else 0, 
                # num_content_demos is removed
                category_model_name="gpt-4.1-mini", 
                content_model_name="gpt-4.1-mini"
            )

            print("\n--- Generated PostData ---")
            print(f"Target Region: {generated_post_obj.region}")
            print(f"Original Item Name: {generated_post_obj.item_name}")
            print(f"Predicted Post Category: {generated_post_obj.category}")
            print(f"Generated Title: {generated_post_obj.title}")
            print(f"Generated Product Image URL: {generated_post_obj.product_image_url}")
            print(f"Generated Content:\n{generated_post_obj.content}")
            print("--------------------------")

        except Exception as e:
            print(f"An error occurred during test generation for item '{test_input_obj.item_name}': {e}")
            import traceback
            traceback.print_exc()

    print("\n--- Post Generator Test Run Complete (Single Master Example Strategy) ---")