# modules/post_generator.py

import json
from typing import Dict, List, Optional, Union 

# Assuming these models and clients are defined in your 'modules' directory
from modules.models import DemoData, InputData, PostData
from modules.openai_client import StandardOpenAIClient # Using your new client
from modules.sampler import Sampler

# --- Regional Placeholders for Demo Formatting ---
# This can be expanded and ideally moved to a separate config/utils file if it grows large
REGIONAL_PLACEHOLDERS = {
    "HK": {
        "recommendation_intro": "發掘 [Product Name]",
        "recommendation_body": "(根據網上搜尋嘅官方資料同專業評測，簡述產品主要功能、獨特賣點同推薦原因...)",
        "reviews_intro": "用家點睇",
        "reviews_body": "(總結網上用家對呢件產品嘅主要好評同常見問題...)",
        "bns_intro": "點解要用BNS由 {warehouse_origin_country} 代運 [Product Name]?",
        "bns_body": "(結合BNS三大優勢「實際重量收費，運費低廉透明」、「免費合併全球14個倉庫包裹」、「實時追蹤，靈活本地派送」，說明點樣幫你買到心頭好...)"
    },
    "TW": {
        "recommendation_intro": "探索 [Product Name]",
        "recommendation_body": "(綜合官方資訊與專業評測，簡述產品主要功能、獨特賣點以及為何推薦...)",
        "reviews_intro": "使用者怎麼說",
        "reviews_body": "(總結網路上使用者回饋，包括常見的讚譽以及可能需注意之處...)",
        "bns_intro": "為何選擇BNS從 {warehouse_origin_country} 代運 [Product Name]?",
        "bns_body": "(結合BNS三大優勢「以實際重量收費，運費低廉透明」、「免費合併全球14處倉庫包裹」、「即時追蹤，彈性本地配送」，說明如何助您輕鬆購得心儀商品...)"
    },
    "EN": { # Default / English example
        "recommendation_intro": "Discover the [Product Name]",
        "recommendation_body": "(Summarize key features, benefits, and why it's a good product, based on web search from official sites and reputable reviews...)",
        "reviews_intro": "What Users Are Saying",
        "reviews_body": "(Summarize common praises and frequent concerns from user reviews found online...)",
        "bns_intro": "Why Shop with BNS for your [Product Name] from {warehouse_origin_country}?",
        "bns_body": "(Explain BNS advantages using the 3 USPs: 'Low, transparent shipping by actual weight', 'Free parcel consolidation across 14 global warehouses', 'Flexible delivery with real-time tracking', tailored to this product and its origin...)"
    }
}

def format_demo_for_category_prompt(demo: DemoData) -> str:
    item_details_str = f"""Item Details:
Item Name: {demo.item_name}
Item's Own Category: {demo.item_category}
Region: {demo.region}"""
    expected_json_output_str = json.dumps({"predicted_category": demo.category}, indent=4, ensure_ascii=False)
    return f"{item_details_str}\n\nExpected JSON Output:\n```json\n{expected_json_output_str}\n```"

def format_demo_for_title_content_prompt(demo: DemoData) -> str:
    item_details_str = f"""Input Item Example (for context and style guidance):
Name: {demo.item_name}
Item's Own Category: {demo.item_category}
Region for Post Style: {demo.region}
Warehouse Location (for context): {demo.warehouse_location}
(Note: For this example, web search would typically be performed for '{demo.item_name}' to generate the detailed content below, but here we use placeholders to demonstrate regional language style and structure.)"""

    placeholders = REGIONAL_PLACEHOLDERS.get(demo.region.upper(), REGIONAL_PLACEHOLDERS["EN"]) 
    
    # Use warehouse_location directly in the placeholder string if needed
    example_content_str = f"""## {placeholders['recommendation_intro'].replace('[Product Name]', demo.item_name)}
{placeholders['recommendation_body']}

## {placeholders['reviews_intro']}
{placeholders['reviews_body']}

## {placeholders['bns_intro'].replace('[Product Name]', demo.item_name).replace('{warehouse_location}', demo.warehouse_location or "the origin warehouse")}
{placeholders['bns_body']}"""

    expected_json_output_str = json.dumps({
        "title": demo.item_name, 
        "content": example_content_str
    }, indent=4, ensure_ascii=False)

    return f"{item_details_str}\n\nExpected JSON Output Example (illustrating structure and language style for region '{demo.region}'):\n```json\n{expected_json_output_str}\n```"

# --- Core Prompting Functions ---

def predict_post_category(
    input_data: InputData,
    available_categories: List[str],
    ai_client: StandardOpenAIClient,
    sampler: Sampler,
    num_demos: int,
    model_name: str = "gpt-4.1-mini"
) -> str:
    system_prompt_1 = """You are an expert AI assistant specializing in e-commerce. Your task is to analyze item details and select the single most appropriate category for a community post about this item from the given list. Respond strictly in the specified JSON format: {"predicted_category": "Chosen Category Name"}."""
    
    if not available_categories:
        raise ValueError("Available categories list cannot be empty.")

    formatted_available_categories = "[\n" + ",\n".join([f'    "{cat}"' for cat in available_categories]) + "\n]"
    
    demos = sampler.retrieve_demos(input_data, num_examples=num_demos)
    formatted_demos_str = "\n\n---\nEXAMPLE:\n".join([format_demo_for_category_prompt(d) for d in demos])
    if formatted_demos_str: formatted_demos_str = "EXAMPLE:\n" + formatted_demos_str

    user_prompt_content = f"""Analyze the item details below and select the MOST appropriate post category from the "Available Post Categories" list.

Available Post Categories:
{formatted_available_categories}

{formatted_demos_str if formatted_demos_str else "No examples provided for context."}

---
Item to categorize:

Item Details:
Item Name: {input_data.item_name}
Item's Own Category: {input_data.item_category}
Region (for context of post): {input_data.region}
URL Extracted Text (if available): {input_data.url_extracted_text or "N/A"}

Based on these details, what is the single most appropriate post category?
Respond strictly with a JSON object: {{"predicted_category": "Chosen Category Name"}}

Expected JSON Output:"""

    messages = [
        {"role": "system", "content": system_prompt_1},
        {"role": "user", "content": user_prompt_content}
    ]
    
    # Using get_completion as this task does not require web search
    raw_json_string = ai_client.get_completion( 
        model=model_name, 
        messages=messages
    )

    if not raw_json_string:
        print(f"Error: No response from AI for category prediction of '{input_data.item_name}'. Defaulting.")
        return available_categories[0] if available_categories else "Other"
        
    try:
        clean_json_string = raw_json_string.strip()
        if clean_json_string.startswith("```json"):
            clean_json_string = clean_json_string[len("```json"):].strip()
        if clean_json_string.endswith("```"):
            clean_json_string = clean_json_string[:-len("```")].strip()
        
        category_data = json.loads(clean_json_string)
        predicted_cat = category_data.get("predicted_category")

        if not predicted_cat or predicted_cat not in available_categories:
            print(f"Warning: LLM predicted category '{predicted_cat}' is invalid or not in available list. Raw: '{raw_json_string}'. Defaulting.")
            return available_categories[0] if available_categories else "Other"
        return predicted_cat
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error parsing category JSON response for '{input_data.item_name}': {e}\nRaw response was: '{raw_json_string}'. Defaulting.")
        return available_categories[0] if available_categories else "Other"


def generate_title_and_content(
    input_data: InputData,
    predicted_post_category: str,
    ai_client: StandardOpenAIClient,
    sampler: Sampler,
    num_demos: int,
    model_name: str = "gpt-4.1-mini"
) -> Dict[str, str]:
    system_prompt_content = f"""You are an Expert Recommender and Content Curator for BNS, a global package forwarding service. Your primary goal is to create informative and appealing marketplace-style posts that help users discover products and understand how BNS can help them acquire these items.

Your task is to:
1.  Thoroughly analyze the provided item details.
2.  **Search the internet to gather fresh and relevant information** about the product. This research will form the basis for the 'Product Recommendation' and 'User Reviews Summary' sections. Focus on factual summaries.
3.  Generate a concise, engaging, product-focused `title`. This title should be based on the item's name ('{input_data.item_name}') but refined by you for clarity, appeal, and suitability as a product listing title.
4.  Generate `content` structured into three specific Markdown sections:
    - `## Discover the {input_data.item_name}`: Based on your internet search of official product websites and reputable expert review sites, summarize the product's key features, compelling benefits, and why it stands out.
    - `## What Users Are Saying`: Based on your internet search of user review aggregators, e-commerce sites, and forums, synthesize common themes from user feedback. Highlight frequently mentioned praises and any notable concerns or drawbacks.
    - `## Why Shop with BNS?`: Explain the advantages of using BNS to purchase this specific item, leveraging the fact that it can be shipped from our warehouse in '{input_data.warehouse_location}'. Weave in these core BNS benefits, tailoring them to the product: 
        1. Low, transparent shipping rates based on actual weight only.
        2. Free parcel consolidation from our 14+ global warehouses lets you shop from multiple stores and save.
        3. Flexible local delivery options with real-time tracking for peace of mind.
5.  Adapt your language, tone, and style to the specified target `region` for the post ('{input_data.region}'). The few-shot examples illustrate how language and style should vary by region.
6.  Your entire response MUST be a single, valid JSON object with exactly two keys: "title" (string) and "content" (string). The `content` string must use Markdown for the section headings as specified.
"""

    demos = sampler.retrieve_demos(input_data, num_examples=num_demos)
    formatted_demos_str = "\n\n---\n".join([format_demo_for_title_content_prompt(d) for d in demos])
    if formatted_demos_str:
        formatted_demos_str = f"Here are some examples of the input item context and the desired JSON output structure with regional style placeholders. These illustrate the expected format and language style for different regions:\n\n{formatted_demos_str}\n\n---"
    else:
        formatted_demos_str = "No examples provided for context. Please rely on the main instructions."

    user_prompt_for_item = f"""{formatted_demos_str}

Now, generate the expert recommender post for the following item.
Remember to:
- **Search the internet comprehensively** for product recommendations and user reviews.
- **Generate a refined title** based on the product's name.
- **Strictly adhere to the JSON output format** (`{{"title": "Your Generated Title", "content": "## Section 1\\n...\\n\\n## Section 2\\n...\\n\\n## Section 3\\n..."}}`) and the three specified Markdown sections in the content.
- **Tailor the language and style** to the target region: '{input_data.region}'.

Item Details for Processing:
- Product Name: {input_data.item_name}
- Item's Own Category (for context): {input_data.item_category}
- Item URL (for context and as a search starting point): {input_data.item_url}
- URL Extracted Text (initial info from product page, if available): {input_data.url_extracted_text or 'N/A'}
- Image URL (for visual context if available, not for direct display in text): {input_data.image_url or 'N/A'}
- Target Region for this Post: {input_data.region}
- BNS Warehouse Location (Origin for "Why BNS" section): {input_data.warehouse_location}
- Discount (if any, mention if significant): {input_data.discount or 'N/A'}
- Post Category (overall category for this BNS post): {predicted_post_category}

Expected JSON Output:"""
    
    messages_for_llm = [{"role": "system", "content": system_prompt_content}]
    
    user_content_payload: Union[str, List[Dict[str, Any]]] = user_prompt_for_item
    if input_data.image_url:
        current_user_content_list = [{"type": "text", "text": user_prompt_for_item}]
        if input_data.image_url.startswith("http://") or input_data.image_url.startswith("https://"):
            current_user_content_list.append({"type": "image_url", "image_url": {"url": input_data.image_url}})
            user_content_payload = current_user_content_list
        else:
            print(f"Warning: Invalid image_url format: {input_data.image_url}. Sending text-only prompt for user content.")
            
    messages_for_llm.append({"role": "user", "content": user_content_payload})

    raw_json_string = ai_client.get_completion_with_search(
        model=model_name,
        messages=messages_for_llm
    )

    default_error_response = {
        "title": f"{input_data.item_name} - Content Generation Error",
        "content": f"## Discover the {input_data.item_name}\nContent generation error.\n\n## What Users Are Saying\nContent generation error.\n\n## Why Shop with BNS?\nContent generation error for item from {input_data.warehouse_location}."
    }

    if not raw_json_string:
        print(f"Error: No response from AI for title/content generation of '{input_data.item_name}'.")
        return default_error_response
        
    try:
        clean_json_string = raw_json_string.strip()
        if clean_json_string.startswith("```json"):
            clean_json_string = clean_json_string[len("```json"):].strip()
        if clean_json_string.endswith("```"):
            clean_json_string = clean_json_string[:-len("```")].strip()

        parsed_data = json.loads(clean_json_string)
        
        final_title = parsed_data.get("title", "").strip()
        final_content = parsed_data.get("content", "").strip()

        if not final_title:
            print(f"Warning: LLM generated an empty title for '{input_data.item_name}'. Using item name as fallback.")
            final_title = input_data.item_name 
        if not final_content or "## Discover" not in final_content: 
            print(f"Warning: LLM generated empty or improperly structured content for '{input_data.item_name}'. Raw: '{raw_json_string}'")
            if not final_content: final_content = "Error: LLM generated empty content."
            # Return the potentially problematic content along with the title, or fallback to default_error_response entirely
            # For now, returning what we got, even if partially malformed.
            # A more robust error handling might return default_error_response here.

        return {"title": final_title, "content": final_content}

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        print(f"Error parsing or validating title/content JSON for '{input_data.item_name}': {e}\nRaw response was: '{raw_json_string}'.")
        return default_error_response


def generate_post_data_from_input(
    input_data_obj: InputData,
    available_categories: List[str],
    ai_client: StandardOpenAIClient, 
    sampler: Sampler,
    num_category_demos: int = 1,
    num_content_demos: int = 1,
    category_model_name: str = "gpt-4.1-mini",
    content_model_name: str = "gpt-4.1-mini"
) -> PostData:
    """
    Orchestrates the generation of a PostData object from an InputData object.
    """
    if not available_categories:
        raise ValueError("Available categories list cannot be empty.")

    print(f"\n--- Generating Post for: {input_data_obj.item_name} (Region: {input_data_obj.region}) ---")

    llm_predicted_post_category = predict_post_category(
        input_data_obj, available_categories, ai_client, sampler, 
        num_demos=num_category_demos, model_name=category_model_name
    )
    print(f"Predicted Post Category for '{input_data_obj.item_name}': {llm_predicted_post_category}")
    
    llm_generated_elements = generate_title_and_content(
        input_data_obj, llm_predicted_post_category, ai_client, sampler,
        num_demos=num_content_demos, model_name=content_model_name
    )
    generated_title = llm_generated_elements.get("title", f"{input_data_obj.item_name} - Title Error")
    print(f"Generated Title for '{input_data_obj.item_name}': {generated_title}")
    
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
        content=llm_generated_elements.get("content", "Error: Content generation failed."),
        discount=input_data_obj.discount,
        payment_method=input_data_obj.payment_method,
        item_weight=input_data_obj.item_weight,
    )
    
    return post_data_instance

# --- Test Execution Block ---
if __name__ == "__main__":
    print("--- Running Post Generator Test (BNS Expert Recommender Persona) ---")

    # This global is for the mock OpenAIClient if it's defined in this file for testing.
    # If you import the actual StandardOpenAIClient, it will use its own config.
    # Ensure your actual StandardOpenAIClient's mock or real implementation is used.
    _MOCK_AVAILABLE_CATEGORIES_FOR_TEST = ["Electronics & Gadgets", "Fashion & Apparel", "Home Goods", "Books", "Travel Gear"]
    
    # Sample InputData for testing
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
            "warehouse_location": "Paris Logistics Center (France)", "item_weight": "2.5 kg", "region": "HK",
            "url_extracted_text": "Ultra-lightweight and durable carry-on, compliant with most airlines. Features 360-degree spinner wheels and a built-in TSA lock.",
            "image_url": None
        }),
    ]
    
    # Sample DemoData for the Sampler
    # The sampler will use these to guide language style.
    sample_demo_data_for_sampler: List[DemoData] = [
        DemoData(post_id="d_us", item_category="Electronics", category="Laptops", item_name="OldLaptop Model A", item_unit_price=800, item_unit_price_currency="USD", item_url="url_us_old", site="OldTechUS", warehouse_id="WH-US-MW", warehouse_location="US-Midwest", region="US", title="Reviewing Model A", content="This is an old style US English post...", like_count=190),
        DemoData(post_id="d_hk", item_category="Travel Gear", category="Luggage", item_name="舊款旅行篋", item_unit_price=500, item_unit_price_currency="HKD", item_url="url_hk_old", site="HKTravel", warehouse_id="WH-HK", warehouse_location="Hong Kong SAR", region="HK", title="舊款旅行篋開箱", content="呢個係舊時嘅香港廣東話風格嘅內容...", like_count=210),
        DemoData(post_id="d_tw", item_category="Electronics", category="Laptops", item_name="舊款筆電C", item_unit_price=25000, item_unit_price_currency="TWD", item_url="url_tw_old", site="TWCompute", warehouse_id="WH-TW", warehouse_location="Taiwan Province of China", region="TW", title="筆電C評測", content="這是舊的台灣國語風格內容...", like_count=150),
    ]
    
    # Instantiate mock/real clients and sampler
    # IMPORTANT: Replace with your actual StandardOpenAIClient instantiation using your config
    # This test assumes StandardOpenAIClient is defined above or imported correctly.
    # You will need a config.ini for the StandardOpenAIClient to initialize.
    try:
        # Create a dummy config.ini for the test if it doesn't exist
        if not os.path.exists('config.ini'):
            print("Creating dummy config.ini for test...")
            dummy_config = configparser.ConfigParser()
            dummy_config['openai'] = {'api_key': 'YOUR_DUMMY_OR_REAL_OPENAI_KEY'}
            with open('config.ini', 'w') as configfile:
                dummy_config.write(configfile)
        
        # The StandardOpenAIClient should be imported from your modules.openai_client
        # For this __main__ block to run, ensure it's either defined above or that
        # modules.openai_client.StandardOpenAIClient can be resolved.
        test_ai_client = StandardOpenAIClient(config_file='config.ini') 
    except Exception as e:
        print(f"Could not initialize StandardOpenAIClient: {e}. Ensure config.ini is set up or mock the client.")
        print("Exiting test.")
        exit()

    sampler_instance = Sampler(all_demo_data=sample_demo_data_for_sampler)

    print(f"\n--- Running pipeline for {len(sample_input_data_list)} items ---")
    for test_input_obj in sample_input_data_list:
        try:
            generated_post = generate_post_data_from_input(
                input_data_obj=test_input_obj,
                available_categories=_MOCK_AVAILABLE_CATEGORIES_FOR_TEST, # Use the test list
                ai_client=test_ai_client,
                sampler=sampler_instance,
                num_category_demos=1, 
                num_content_demos=1,
                category_model_name="gpt-4.1-mini",
                content_model_name="gpt-4.1-mini" # Or another capable model
            )

            print("\n--- Generated PostData ---")
            print(f"Target Region: {generated_post.region}")
            print(f"Original Item Name: {generated_post.item_name}")
            print(f"Predicted Post Category: {generated_post.category}")
            print(f"Generated Title: {generated_post.title}")
            print(f"Generated Content:\n{generated_post.content}")
            print("--------------------------")

        except Exception as e:
            print(f"An error occurred during test generation for item '{test_input_obj.item_name}': {e}")
            import traceback
            traceback.print_exc()

    print("\n--- Post Generator Test Run Complete ---")