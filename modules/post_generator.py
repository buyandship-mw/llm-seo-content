# modules/post_generator.py

import json
from typing import Dict, List, Optional, Union, Any

from modules.models import DemoData, InputData, PostData
from modules.openai_client import OpenAIClient, extract_and_parse_json # Using your client
from modules.sampler import Sampler

def format_demo_for_category_prompt(demo: DemoData) -> str:
    # This function remains unchanged as per our discussion.
    item_details_str = f"""Item Details:
Item Name: {demo.item_name}
Item's Own Category: {demo.item_category}
Region: {demo.region}"""
    expected_json_output_str = json.dumps({"predicted_category": demo.category}, indent=4, ensure_ascii=False)
    return f"{item_details_str}\n\nExpected JSON Output:\n```json\n{expected_json_output_str}\n```"

def predict_post_category(
    input_data: InputData,
    available_categories: List[str],
    ai_client: OpenAIClient,
    sampler: Sampler,
    num_demos: int,
    model_name: str = "gpt-4.1-mini"
) -> str:
    # This function remains unchanged as per our discussion.
    system_prompt_1 = """You are an expert AI assistant specializing in e-commerce. Your task is to analyze item details and select the single most appropriate category for a community post about this item from the given list. Respond strictly in the specified JSON format: {"predicted_category": "Chosen Category Name"}."""
    
    if not available_categories:
        # Fallback if no categories are provided; could also raise an error.
        print("Warning: available_categories list is empty in predict_post_category. Defaulting to 'Other'.")
        return "Other"

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
            # If available_categories is empty, we can't check against it, so we trust the LLM prediction if it's a string.
            if available_categories: # Only print "not in available list" if the list exists
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

def format_demo_for_title_content_prompt(demo: DemoData) -> str:
    # This function shows how an input 'demo' item translates to an ideal JSON output.
    # The 'demo.content' itself is used as a language style reference.
    # The 'expected_json_output_str' below illustrates the target structure,
    # including how section headers should be dynamically generated by the LLM
    # in the style of 'demo.region'.

    item_details_str = f"""Input Item Example (for context and style guidance):
Name: {demo.item_name}
Item's Own Category: {demo.item_category}
Region for Post Style: {demo.region}
Warehouse Location (for BNS context): {demo.warehouse_location}"""

    # Construct an idealized example of Markdown content.
    # These section headers are EXAMPLES of what the LLM should generate,
    # translated and styled for the demo's region.
    # The body text is illustrative of structure (short, lists) and style.
    example_title_for_json = demo.title # Assuming demo.title is already a good, translated example
    example_markdown_content = ""
    # Using f-strings carefully to avoid issues with curly braces inside JSON within f-string.
    warehouse_location_placeholder = demo.warehouse_location or ('海外' if demo.region == "HK" else '國外' if demo.region == "TW" else 'origin')

    if demo.region == "HK":
        example_markdown_content = f"""## ✨ 發掘產品嘅獨特之處 ✨
呢件產品有好多令人驚喜嘅功能，例如... (簡短介紹，突出賣點)
- 主要功能A：詳細說明
- 賣點B：點樣幫到你

## 🗣️ 香港人點睇？
好多本地用家都話：
- 讚賞點：(例如：「電量好襟用，用到一日都仲得！」)
- 可能要注意：(例如：「個app有時有啲慢。」)

## 🚚 點解揀BNS？
BNS幫你輕鬆買到心頭好：
- 運費按實際重量計，平靚正。
- 免費將唔同地方買嘅貨夾埋一齊寄。
- 送貨選擇夠彈性，隨時check到件貨去咗邊。"""
    elif demo.region == "TW":
        example_markdown_content = f"""## 🌟 探索 {demo.item_name} 的亮點 🌟
這款產品擁有許多令人驚艷的特色，例如... (簡短介紹，強調賣點)
- 主要特色1：詳細描述
- 獨特優勢2：如何解決您的需求

## 💬 台灣使用者怎麼說？
許多台灣使用者回饋：
- 優點：(例如：「電池續航力超強，用一整天沒問題！」)
- 需注意：(例如：「應用程式偶爾反應較慢。」)

## 🚀 為何選擇BNS？
BNS助您輕鬆購得心儀商品：
- 實際重量計費，運費低廉透明。
- 免費合併多國包裹，節省更多。
- 即時追蹤，彈性本地配送。"""
    else: # Default EN
        example_markdown_content = f"""## ✨ Discover the Allure of the {demo.item_name} ✨
This product boasts several standout features, such as... (Brief, engaging intro)
- Key Feature A: Description
- Unique Selling Point B: How it benefits you

## 🗣️ What Users Are Saying
Users frequently mention:
- Praises: (e.g., "The battery life is amazing, easily lasts a full day!")
- Concerns: (e.g., "The companion app can be a bit sluggish at times.")

## 🚚 Why Use BNS to Ship Your {demo.item_name} from {warehouse_location_placeholder}?
BNS makes it easy to get what you want:
- Low, transparent shipping by actual weight.
- Free parcel consolidation from global warehouses.
- Flexible local delivery with real-time tracking."""

    expected_json_output_str = json.dumps({
        "title": example_title_for_json,
        "product_image_url": f"http://example.com/images/{demo.item_name.replace(' ', '_').lower()}_demo.jpg", # Placeholder
        "content": example_markdown_content
    }, indent=4, ensure_ascii=False)

    original_style_reference = f"""Original Content for Language Style Reference (Region: {demo.region}):
```text
{demo.content}
```"""

    return f"{item_details_str}\n\n{original_style_reference}\n\nExpected JSON Output Example (illustrating target structure, regional language style, and LLM-generated section headers):\n```json\n{expected_json_output_str}\n```"


def generate_post_body(
    input_data: InputData,
    predicted_post_category: str,
    ai_client: OpenAIClient,
    sampler: Sampler,
    num_demos: int,
    model_name: str = "gpt-4.1-mini"
) -> Dict[str, Any]:
    
    system_prompt_content = f"""You are an Expert Recommender and Content Curator for BNS, a global package forwarding service. Your primary goal is to create informative, appealing, and mobile-first marketplace-style posts.

Your task is to:
1.  Thoroughly analyze the provided item details.
2.  **Search the internet to gather fresh and relevant information** about the product (features, benefits, user reviews) and to **find a publicly accessible URL for a high-quality product image**.
3.  Generate a concise, engaging, product-focused `title`. **This title MUST be in the language and style appropriate for the target `region` ('{input_data.region}')**.
4.  Generate Markdown `content` structured into three specific sections. For each section:
    a.  **Create an engaging H2 Markdown heading (e.g., `## Your Engaging Regional Heading`)**. This heading must be appropriate for the section's content, translated into the target `region`'s language, and incorporate the product name naturally where suitable (especially the first section).
    b.  Populate the section with informative content, adhering to mobile-first readability (short paragraphs, scannability). Use Markdown bullet points (`-` or `*`) for lists. Avoid excessive repetition of the product name after its initial prominent mentions.
5.  The three content sections are:
    * **Section 1: Product Introduction & Key Appeal.** Based on your web search, provide a compelling intro. Start with a highly scannable, mobile-first summary of the product and its core appeal. Then, elaborate on key features and benefits.
    * **Section 2: User Review Summary.** Summarize common themes from user feedback (web search). **Cite specific examples or details for praises and concerns** (e.g., "users loved the long battery life, often citing 18-20 hours of use" or "some found the X feature difficult to set up").
    * **Section 3: Why Shop with BNS?** Explain the advantages of using BNS for this item from '{input_data.warehouse_location}'. Detail BNS's core benefits (low actual weight shipping, free parcel consolidation, flexible delivery/tracking) as a bulleted list, tailored to the product.
6.  Adapt your language, tone, and overall style to the specified target `region` ('{input_data.region}'). The few-shot examples (especially their 'Original Content for Language Style Reference') illustrate the desired linguistic style.
7.  Your entire response MUST be a single, valid JSON object with exactly three keys: "title" (string), "product_image_url" (string, or `null` if not found), and "content" (string with Markdown).
"""

    demos = sampler.retrieve_demos(input_data, num_examples=num_demos)
    formatted_demos_str = "\n\n---\n".join([format_demo_for_title_content_prompt(d) for d in demos])
    if formatted_demos_str:
        formatted_demos_str = f"""Here are some examples. For each, we provide the input item context, its original content (as a language style reference), and an example of the desired JSON output structure.
Adapt the language style from the 'Original Content for Language Style Reference' of the most relevant demo(s) to the structured JSON output format when generating the response for the new item.

{formatted_demos_str}

---"""
    else:
        formatted_demos_str = "No examples provided for context. Please rely on the main instructions."

    user_prompt_for_item = f"""{formatted_demos_str}

Now, generate the expert recommender post for the following item.
Remember to:
- **Search the internet comprehensively** for product information, user reviews, and a product image URL.
- **Generate a refined, translated title** and **region-specific, LLM-generated section headers**.
- **Strictly adhere to the JSON output format** (`{{"title": "...", "product_image_url": "...", "content": "## Section 1 Header\\n...\\n\\n## Section 2 Header\\n...\\n\\n## Section 3 Header\\n..."}}`) and the three specified Markdown sections.
- **Tailor the language and style** (based on demo style references if available) to the target region: '{input_data.region}'.

Item Details for Processing:
- Product Name: {input_data.item_name}
- Item's Own Category (for context): {input_data.item_category}
- Item URL (for context and as a search starting point): {input_data.item_url}
- URL Extracted Text (initial info, if available): {input_data.url_extracted_text or 'N/A'}
- Image URL (from input, for visual context if model is vision-capable, if available): {input_data.image_url or 'N/A'}
- Target Region for this Post: {input_data.region}
- BNS Warehouse Location (Origin for "Why BNS" section): {input_data.warehouse_location}
- Discount (if any, mention if significant): {input_data.discount or 'N/A'}
- Post Category (overall BNS post category): {predicted_post_category}

Expected JSON Output:"""
    
    messages_for_llm = [{"role": "system", "content": system_prompt_content}]
    
    user_content_payload: Union[str, List[Dict[str, Any]]] = user_prompt_for_item
    if input_data.image_url and (input_data.image_url.startswith("http://") or input_data.image_url.startswith("https://")):
        # This structure is for OpenAI's vision-capable models.
        # Adjust if your client/model expects a different format.
        current_user_content_list = [{"type": "text", "text": user_prompt_for_item}]
        current_user_content_list.append({"type": "image_url", "image_url": {"url": input_data.image_url, "detail": "auto"}}) # Added detail auto
        user_content_payload = current_user_content_list
        print(f"Info: Sending image URL {input_data.image_url} to vision-capable model for item '{input_data.item_name}'.")
    
    messages_for_llm.append({"role": "user", "content": user_content_payload})

    raw_json_string = ai_client.get_completion(
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
        parsed_data = extract_and_parse_json(raw_json_string) # Assumes this handles the "```json\n ... \n```" stripping
        
        if not isinstance(parsed_data, dict):
            print(f"Error: Parsed JSON for post body is not a dictionary for '{input_data.item_name}'. Raw: '{raw_json_string}'.")
            return default_error_response

        final_title_raw = parsed_data.get("title")
        final_content_raw = parsed_data.get("content")
        product_image_url_raw = parsed_data.get("product_image_url")

        # Validate title
        if isinstance(final_title_raw, str) and final_title_raw.strip():
            final_title = final_title_raw.strip()
        else:
            print(f"Warning: 'title' from LLM is invalid or empty for '{input_data.item_name}'. Got: '{final_title_raw}'. Using item name as fallback. Raw response: '{raw_json_string}'.")
            final_title = input_data.item_name

        # Validate content
        if isinstance(final_content_raw, str) and final_content_raw.strip():
            final_content = final_content_raw.strip()
        else:
            print(f"Warning: 'content' from LLM is invalid or empty for '{input_data.item_name}'. Got: '{final_content_raw}'. Using error content. Raw response: '{raw_json_string}'.")
            # Construct a minimal error content matching the expected structure
            final_content = f"## Content Error for {final_title}\nCould not generate product details.\n\n## User Feedback Error\nCould not generate user feedback summary.\n\n## BNS Information Error\nCould not generate BNS advantages."
        
        # Validate product_image_url (can be string or null/None)
        product_image_url: Optional[str] = None
        if isinstance(product_image_url_raw, str) and product_image_url_raw.strip():
            # Basic URL validation (starts with http/https)
            if product_image_url_raw.startswith("http://") or product_image_url_raw.startswith("https://"):
                product_image_url = product_image_url_raw
            else:
                print(f"Warning: 'product_image_url' ('{product_image_url_raw}') from LLM is not a valid URL for '{input_data.item_name}'. Setting to None. Raw response: '{raw_json_string}'.")
                product_image_url = None
        elif product_image_url_raw is not None: # If it's not a string and not None (e.g. empty string, int)
            print(f"Warning: 'product_image_url' from LLM is not a string or null for '{input_data.item_name}'. Got: '{product_image_url_raw}'. Setting to None. Raw response: '{raw_json_string}'.")
            product_image_url = None
        # If product_image_url_raw is None, it remains None, which is valid.

        return {"title": final_title, "content": final_content, "product_image_url": product_image_url}

    except json.JSONDecodeError as e:
        print(f"Error parsing post body JSON for '{input_data.item_name}': {e}\nRaw response was: '{raw_json_string}'.")
        return default_error_response
    except Exception as e: 
        print(f"Unexpected error processing parsed post body JSON for '{input_data.item_name}': {e}\nRaw response was: '{raw_json_string}'.")
        return default_error_response


def compile_post_data(
    input_data_obj: InputData,
    available_categories: List[str],
    ai_client: OpenAIClient, 
    sampler: Sampler,
    num_category_demos: int = 1,
    num_content_demos: int = 1,
    category_model_name: str = "gpt-4.1-mini",
    content_model_name: str = "gpt-4.1-mini" # Consider gpt-4-turbo or gpt-4o for better complex generation
) -> PostData:
    """
    Orchestrates the generation of a PostData object from an InputData object.
    It first predicts the category, then generates the title, content, and image URL.
    """
    print(f"\n--- Compiling Post Data for: {input_data_obj.item_name} (Region: {input_data_obj.region}) ---")

    # 1. Predict Category
    llm_predicted_post_category = predict_post_category(
        input_data_obj, available_categories, ai_client, sampler, 
        num_demos=num_category_demos, model_name=category_model_name
    )
    print(f"Predicted Post Category for '{input_data_obj.item_name}': {llm_predicted_post_category}")
    
    # 2. Generate Post Body (Title, Content, Image URL)
    post_body_elements = generate_post_body(
        input_data_obj, 
        llm_predicted_post_category, 
        ai_client, 
        sampler,
        num_demos=num_content_demos, 
        model_name=content_model_name
    )
    generated_title = post_body_elements.get("title") # Already defaulted in generate_post_body
    generated_content = post_body_elements.get("content") # Already defaulted
    generated_image_url = post_body_elements.get("product_image_url") # Can be None

    print(f"Generated Title for '{input_data_obj.item_name}': {generated_title}")
    if generated_image_url:
        print(f"Generated Product Image URL: {generated_image_url}")
    else:
        print(f"No Product Image URL generated or found for '{input_data_obj.item_name}'.")
    
    # 3. Construct PostData
    # (Assuming PostData model is updated to include product_image_url and handles all fields)
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
        product_image_url=generated_image_url, # New field
        discount=input_data_obj.discount,
        payment_method=input_data_obj.payment_method,
        item_weight=input_data_obj.item_weight,
    )
    
    return post_data_instance

# --- Test Execution Block ---
if __name__ == "__main__":
    print("--- Running Post Generator Test (BNS Expert Recommender Persona - Revised) ---")

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
            "warehouse_location": "Paris Logistics Center (France)", "item_weight": "2.5 kg", "region": "HK",
            "url_extracted_text": "Ultra-lightweight and durable carry-on, compliant with most airlines. Features 360-degree spinner wheels and a built-in TSA lock.",
            "image_url": None
        }),
         InputData(**{
            "item_category": "Beauty", "discount": "5%", "item_name": "Sakura Bloom Face Cream",
            "item_unit_price": 750.00, "item_unit_price_currency": "TWD", "item_url": "http://example.com/sakuracream",
            "payment_method": "Credit Card", "site": "TWBeautyFinds.com", "warehouse_id": "WH-TW",
            "warehouse_location": "Taoyuan Logistics (Taiwan)", "item_weight": "0.2 kg", "region": "TW",
            "url_extracted_text": "Rich moisturizing cream with sakura extract for radiant skin. Suitable for all skin types.",
            "image_url": "https://example.com/images/sakura_face_cream.jpg" # Example valid image URL
        }),
    ]
    
    sample_demo_data_for_sampler: List[DemoData] = [
        DemoData(post_id="d_us_electronics", item_category="Electronics", category="Laptops", 
                 item_name="OldLaptop Model A (US Demo)", item_unit_price=800, item_unit_price_currency="USD", 
                 item_url="url_us_old", site="OldTechUS", warehouse_id="WH-US-MW", warehouse_location="US-Midwest", 
                 region="US", 
                 title="Model A Laptop: A US Perspective", # Good example US title
                 content="This is some classic American English tech review style content. It talks about specs, performance, and maybe compares it to other models. The tone is generally informative and direct. We're looking for this kind of vibe for US posts. It often includes direct comparisons and value propositions.", # Language style reference
                 like_count=190),
        DemoData(post_id="d_hk_luggage", item_category="Travel Gear", category="Luggage", 
                 item_name="舊款旅行篋 (HK Demo)", item_unit_price=500, item_unit_price_currency="HKD", 
                 item_url="url_hk_old", site="HKTravel", warehouse_id="WH-HK", warehouse_location="Hong Kong SAR", 
                 region="HK", 
                 title="【香港實試】舊款旅行篋值唔值得買？", # Good example HK title
                 content="呢篇嘢會用好地道嘅廣東話去講下呢個喼。會講下佢嘅物料啊、轆仔順唔順啊、拉鍊實唔實啊咁。啲語氣可能會比較輕鬆活潑啲，有時仲會加啲潮語、hashtag。主要係想俾香港嘅朋友仔一個參考，等佢哋買得開心又放心。", # Language style reference
                 like_count=210),
        DemoData(post_id="d_tw_beauty", item_category="Beauty", category="Skincare", 
                 item_name="櫻花面霜 (TW Demo)", item_unit_price=25000, item_unit_price_currency="TWD", 
                 item_url="url_tw_old", site="TWBeautyFindsTW", warehouse_id="WH-TW", warehouse_location="Taiwan Province of China", # Corrected site for demo consistency
                 region="TW", 
                 title="台灣網友激推！櫻花面霜深度評測保養祕訣大公開", # Good example TW title
                 content="這篇文章會用台灣國語來寫，風格可能會比較注重細節跟使用感受，比如說擦起來的質地啦、保濕度夠不夠力啊、香味怎麼樣之類的。可能也會有一些比較可愛或者溫柔的語氣詞，像是「超好用der～」、「CP值很高唷！」。整體來說，是想提供詳細又親切的資訊給台灣的消費者。", # Language style reference
                 like_count=150),
    ]
    
    try:
        # Ensure your OpenAIClient is correctly initialized.
        # For testing, you might point to a mock client or ensure API keys are set in config.ini
        test_ai_client = OpenAIClient(config_file='config.ini') 
        # test_ai_client.set_mock_mode(True) # If your client has a mock mode for testing without API calls
    except Exception as e:
        print(f"Could not initialize OpenAIClient: {e}. Ensure config.ini is set up or mock the client for testing.")
        print("Exiting test.")
        exit()

    sampler_instance = Sampler(all_demo_data=sample_demo_data_for_sampler)

    print(f"\n--- Running pipeline for {len(sample_input_data_list)} items ---")
    for test_input_obj in sample_input_data_list:
        try:
            generated_post_obj = compile_post_data(
                input_data_obj=test_input_obj,
                available_categories=_MOCK_AVAILABLE_CATEGORIES_FOR_TEST,
                ai_client=test_ai_client,
                sampler=sampler_instance,
                num_category_demos=1, 
                num_content_demos=1,
                category_model_name="gpt-4.1-mini", 
                content_model_name="gpt-4-turbo" # Using a more capable model for content as suggested in thoughts.
                                                 # User can change to "gpt-4.1-mini" if preferred/cost-sensitive.
            )

            print("\n--- Generated PostData ---")
            print(f"Target Region: {generated_post_obj.region}")
            print(f"Original Item Name: {generated_post_obj.item_name}")
            print(f"Predicted Post Category: {generated_post_obj.category}")
            print(f"Generated Title: {generated_post_obj.title}")
            print(f"Generated Product Image URL: {generated_post_obj.product_image_url}") # Print new field
            print(f"Generated Content:\n{generated_post_obj.content}")
            print("--------------------------")

        except Exception as e:
            print(f"An error occurred during test generation for item '{test_input_obj.item_name}': {e}")
            import traceback
            traceback.print_exc()

    print("\n--- Post Generator Test Run Complete ---")