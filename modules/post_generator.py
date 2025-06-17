# modules/post_generator.py
import json
import os
from typing import Dict, List, Optional, Any, Tuple

from modules.models import PostData, Category, Warehouse, Interest
from modules.openai_client import OpenAIClient, extract_and_parse_json # Using your client
from modules.csv_parser import load_forex_rates_from_json
from utils.currency import convert_price

# --- Module Constants ---
MASTER_POST_EXAMPLES: Dict[str, List[Dict[str, str]]] = {
    "HK": [{
        "item_url": "https://www.target.com/p/fujifilm-instax-mini-12-camera/-/A-88743864",
        "item_name": "Fujifilm Instax Mini 12 Camera",
        "warehouse": "warehouse-4px-uspdx",
        "title": "📸 Fujifilm Instax Mini 12",
        "content":
            """
- 得意設計＋超易用
- 自動曝光，唔使調光
- 自拍模式＋自拍鏡
- 約 5 秒即印，即影即分享
- 紫色款，打卡又靚又有型

用家評價
👍 易用、靚設計，新手啱用
⚠️ 強光下會過曝，要小心使用
            """
    }, {
        "item_url": "https://www.gourmandise.jp/view/item/000000009318",
        "item_name": "Chiikawa 完全無線立體聲耳機",
        "warehouse": "warehouse-qs-osaka",
        "title": "🎧 Chiikawa 完全無線立體聲耳機",
        "content":
            """
- 可愛嘅 Chiikawa 角色設計
- 耳塞式設計，確保音質清晰
- 支援藍牙連接，8米內無線播放音樂
- 耳機上嘅觸控開關，方便操作

用家評價
👍 可愛嘅設計，音質清晰，連接穩定
⚠️ 連續使用時間較短，需要經常充電
            """
    }]
}

DEFAULT_FALLBACK_IMAGE_URL = "https://example.com/default_item_image.png"

# --- Internal Helper Functions ---

def _build_comprehensive_llm_prompt(
    client_input: PostData,
    available_bns_categories: List[Category],
    available_interests: List[Interest],
    valid_warehouses_for_mcq: List[str]  # Just the warehouse codes for the prompt
) -> Tuple[str, List[str]]:
    prompt_lines = []
    category_labels = [c.label for c in available_bns_categories]
    interest_labels = [i.label for i in available_interests]

    tld_warehouse_map = {
        "jp": "warehouse-qs-osaka",
        "us": "warehouse-4px-uspdx",
        "uk": "warehouse-bnsuk-ashford",
        "ca": "warehouse-bnsca-toronto",
        "it": "warehouse-bnsit-milan",
        "au": "warehouse-bnsau-sydney",
        "kr": "warehouse-kas-seoul",
        "hk": "warehouse-bns-hk",
        "cn": "warehouse-lht-dongguan",
        "tw": "warehouse-bnstw-taipei",
        "th": "warehouse-bnsth-bangkok",
        "id": "warehouse-bnsid-jakarta",
    }

    # --- Lists the model can choose from (moved to top) ---
    prompt_lines.append("### SELECTABLE OPTIONS")
    prompt_lines.append(f"Warehouses: {valid_warehouses_for_mcq}")
    prompt_lines.append(f"Categories: {category_labels}")
    prompt_lines.append(f"Interests: {interest_labels}")
    prompt_lines.append(
        "You may ONLY choose values from these lists. Never invent new warehouses, categories, or interests."
    )

    # --- Step-by-step workflow ---
    prompt_lines.append(
        "\n--- STEP-BY-STEP WORKFLOW ---"
        "\n1. Parse all provided fields, noting any pre-filled values."
        "\n2. Scraped data may already include item_name, price, or currency. "
        "\nIf item_weight is missing, search the product details to find it in grams. If unavailable, return None."
        "\nIf price or currency are missing, try to determine them. "
        "\nAlso attempt your own item_name and later compare it with the scraped value."
        "\n3. Extract each required data field. If information is unavailable, return None."
        "\n4. Select the most suitable category, warehouse, and interest from the lists above (never create new values)."
        "\n5. Generate region-specific 'title' and 'content' matching the tone and structure of the provided examples."
        "\n6. Output a single valid JSON object using the structure below with no commentary or markdown."
    )

    # --- Output format & guardrails ---
    prompt_lines.append("\n--- REQUIRED JSON OUTPUT STRUCTURE ---")
    prompt_lines.append(
        "Your entire response MUST be exactly one JSON object with these keys. Use the fallbacks above whenever a value can't be found."
    )

    output_fields = ["item_name", "category", "interest", "warehouse", "title", "content"]
    if client_input.item_weight is None:
        output_fields.append("item_weight")
    if not client_input.source_price:
        output_fields.append("source_price")
    if not client_input.source_currency:
        output_fields.append("source_currency")

    field_desc = {
        "item_name": '  "item_name": "string"',
        "category": '  "category": "string_from_list"',
        "warehouse": '  "warehouse": "string_from_list_or_client_value"',
        "interest": '  "interest": "string_from_list"',
        "source_currency": '  "source_currency": "3_letter_code_or_\"N/A\""',
        "source_price": '  "source_price": "float"',
        "title": '  "title": "string"',
        "content": '  "content": "string_plain_text"',
        "item_weight": '  "item_weight": "float_or_null"',
    }

    output_lines = ["{\n"]
    for idx, key in enumerate(output_fields):
        comma = "," if idx < len(output_fields) - 1 else ""
        output_lines.append(f"{field_desc[key]}{comma}\n")
    output_lines.append("}")
    prompt_lines.append("".join(output_lines))
    prompt_lines.append(
        "Reminder: Only use the provided lists for category, interest, and warehouse. If uncertain, default to the first list item."
    )

    prompt_lines.append("\n--- CLIENT-PROVIDED DATA & INSTRUCTIONS ---")
    prompt_lines.append(f"Item URL to analyze: {client_input.item_url}")
    prompt_lines.append(f"Target region for the post style: {client_input.region}")

    # Field-specific instructions
    # item_name
    prompt_lines.append(
        "\n--- ITEM NAME EXTRACTION & TRANSLATION ---"
    )
    if client_input.item_name:
        prompt_lines.append(
            f"- A scraper found the name '{client_input.item_name}'. "
            "Translate this item name to English, then compare with the scraped name. "
            "Choose the most clear English name and place it in the 'item_name' field."
        )
    else:
        prompt_lines.append(
            f"- Determine the item's name from '{client_input.item_url}'. "
            "Translate the extracted name to English and place the result in the 'item_name' field."
        )

    # warehouse (MCQ)
    prompt_lines.append(
        f"- Infer the primary sales country from {client_input.item_url} and related details."
    )
    prompt_lines.append(
        f"- Use this heuristic mapping for quick selection based on the URL's top-level domain: {tld_warehouse_map}."
    )
    prompt_lines.append(
        f"- Choose the warehouse from {valid_warehouses_for_mcq} that best matches or is geographically closest to that country. If unsure, default to 'warehouse-bns-hk'."
    )

    # category (MCQ)
    prompt_lines.append(
        f"- From the following list of valid BNS Post Categories: {category_labels}, select the single most appropriate category for the item based on all its details. Place your choice in the 'category' field."
    )

    # interest (MCQ)
    prompt_lines.append(
        f"- From the following list of valid interests: {interest_labels}, select the single most appropriate interest for the item. Place your choice in the 'interest' field."
    )

    # source_currency & source_price
    if client_input.source_price > 0 or client_input.source_currency:
        prompt_lines.append(
            "- Use any provided 'source_price' or 'source_currency' values as-is. "
            "Only determine whichever of these two fields is missing."
        )
    else:
        prompt_lines.append(
            f"- Determine the item's price from '{client_input.item_url}'. Extract the numeric price and currency. "
            "Convert the currency to its three-letter code (e.g., USD). "
            "Place the numeric price in 'source_price' and the code in 'source_currency'. "
            "If price is not found, use None for price and None for currency."
        )
    
    # title & content
    master_examples_list_for_region = MASTER_POST_EXAMPLES.get(client_input.region.upper())
    if not master_examples_list_for_region: # Check if the list is None or empty
        raise NotImplementedError(
            f"CRITICAL PROMPT WARNING: No master examples found for region '{client_input.region}'. "
            "ICL for title/content will not be effective."
        )
    else:
        master_examples_json_str = json.dumps(master_examples_list_for_region, ensure_ascii=False, indent=2)
        language_guidance = (
            f"Both title and content must be in the same language as these master examples for '{client_input.region}', "
            "and content should similarly match their language style."
        )

    prompt_lines.append(
        "\n--- CONTENT GENERATION (TITLE & CONTENT) ---"
        "\nBased on all information (client-provided and your findings from your simulated search), "
        "generate 'title' (string) and 'content' (string, plain text, NO MARKDOWN formatting)."
    )
    prompt_lines.append(
        f"The style, tone, and structure for 'title' and 'content' should be closely guided by the master examples "
        f"provided below for the {client_input.region} region. {language_guidance} "
        "The 'content' should generally have two main sections based on your simulated search: "
        "1. a product introduction (highlighting key features/benefits), and "
        "2. a brief summary of user reviews or public sentiment."
    )
    prompt_lines.append(
        f"Here are some master examples for your reference. Learn from their structure, "
        f"item details they choose to highlight, and how they phrase the title and content sections:\n"
        f"{master_examples_json_str}"
    )

    prompt = "\n\n".join(prompt_lines)
    print(prompt)

    return prompt, output_fields

def _invoke_comprehensive_llm(
    user_prompt: str,
    ai_client: OpenAIClient,
    model: str,
    expected_keys: List[str]
) -> Optional[Dict[str, Any]]:
    messages = [{"role": "user", "content": user_prompt}]
    raw_response_str = ai_client.get_completion_with_search(model=model, messages=messages)

    if raw_response_str:
        parsed_json = extract_and_parse_json(raw_response_str)
        print(f"DEBUG: Raw LLM response: {parsed_json}")
        if isinstance(parsed_json, dict):
            # Validate that all expected keys are present in LLM response
            missing_keys = [key for key in expected_keys if key not in parsed_json]
            if missing_keys:
                print(f"Warning: LLM response missing required keys: {missing_keys}. Raw: {raw_response_str}")
            return parsed_json
        else:
            print(f"Warning: LLM response was not a valid JSON dictionary. Raw: {raw_response_str}")
    return None

def _finalize_data_from_llm_response(
    llm_output: Dict[str, Any],
    original_client_input: PostData,
    available_bns_categories: List[Category],
    available_interests: List[Interest],
    valid_warehouses: List[Warehouse],
    currency_conversion_rates: Dict[str, Dict[str, float]]
) -> Dict[str, Any]:
    final_data = {}

    # --- Required fields from client input, passed through ---
    final_data["item_url"] = original_client_input.item_url
    final_data["region"] = original_client_input.region

    # --- Optional fields from client input, passed through ---
    final_data["user"] = original_client_input.user
    final_data["status"] = original_client_input.status
    final_data["is_pinned"] = original_client_input.is_pinned
    final_data["pinned_end_datetime"] = original_client_input.pinned_end_datetime
    final_data["pinned_expire_hours"] = original_client_input.pinned_expire_hours
    final_data["disable_comment"] = original_client_input.disable_comment
    final_data["team_id"] = original_client_input.team_id
    final_data["payment_method"] = original_client_input.payment_method
    final_data["item_weight"] = original_client_input.item_weight
    final_data["discounted"] = original_client_input.discounted

    # --- Scraper output, passed through ---
    final_data["image_url"] = original_client_input.image_url

    # --- Apply LLM fallbacks ---
    if original_client_input.item_weight is None:
        final_data["item_weight"] = llm_output.get("item_weight")
    else:
        final_data["item_weight"] = original_client_input.item_weight

    if original_client_input.source_price is None:
        final_data["source_price"] = llm_output.get("source_price")
    else:
        final_data["source_price"] = original_client_input.source_price
    
    if original_client_input.source_currency is None:
        final_data["source_currency"] = llm_output.get("source_currency")
    else:
        final_data["source_currency"] = original_client_input.source_currency

    # --- Apply LLM generated / transformed output ---
    final_data["item_name"] = llm_output.get("item_name")
    final_data["title"] = llm_output.get("title")
    final_data["content"] = llm_output.get("content")

    # Validate warehouse selection and get currency
    warehouse = llm_output.get("warehouse")
    target_warehouse = next((wh for wh in valid_warehouses if wh.value == warehouse), None)

    if not target_warehouse:
        print("Warning: Client/LLM warehouse invalid or missing. Defaulting warehouse from valid list.")
        target_warehouse = valid_warehouses[0]

    final_data["warehouse"] = target_warehouse.value
    target_currency = target_warehouse.currency.upper()

    # Perform price conversion to target_currency
    source_price = final_data.get("source_price", 0.0)
    source_currency = final_data.get("source_currency", None)

    if source_price is not None and source_currency and target_currency not in ["N/A", None]:
        if source_currency == target_currency:
            final_item_price_converted = source_price
        else:
            converted = convert_price(
                source_price,
                source_currency,
                target_currency,
                currency_conversion_rates,
            )
            if converted is not None:
                final_item_price_converted = converted
            else:
                print(f"Warning: Conversion failed from {source_currency} to {target_currency}. Using 0.0.")
                final_item_price_converted = 0.0
    else:
        print(f"Warning: Target warehouse currency is '{target_currency}'. Using 0.0 as price in target currency.")
        final_item_price_converted = 0.0

    final_data["item_unit_price"] = final_item_price_converted

    # 4. category (convert label to numeric value)
    label_to_value = {c.label: c.value for c in available_bns_categories}
    values = set(label_to_value.values())
    if original_client_input.category and original_client_input.category in values:
        final_data["category"] = original_client_input.category
    elif "category" in llm_output and llm_output["category"] in label_to_value:
        final_data["category"] = label_to_value[llm_output["category"]]
    elif values:
        print(
            "Warning: Client/LLM category invalid or missing. Defaulting from valid list."
        )
        final_data["category"] = next(iter(values))

    # 5. interest (convert label to value)
    label_to_interest_value = {i.label: i.value for i in available_interests}
    interest_values = set(label_to_interest_value.values())
    if original_client_input.interest and original_client_input.interest in interest_values:
        final_data["interest"] = original_client_input.interest
    elif "interest" in llm_output and llm_output["interest"] in label_to_interest_value:
        final_data["interest"] = label_to_interest_value[llm_output["interest"]]
    elif interest_values:
        print(
            "Warning: Client/LLM interest invalid or missing. Defaulting from valid list."
        )
        final_data["interest"] = next(iter(interest_values))

    return final_data

# --- Public API Function ---
def generate_post(
    client_input: PostData,
    available_bns_categories: List[Category],
    available_interests: List[Interest],
    valid_warehouses: List[Warehouse],
    currency_conversion_rates: Dict[str, Dict[str, float]],
    ai_client: OpenAIClient,
    model: str
) -> PostData:
    print(f"INFO: Starting post generation for URL: {client_input.item_url}, Region: {client_input.region}")


    valid_warehouses_for_prompt = [wh.value for wh in valid_warehouses]

    user_prompt, expected_keys = _build_comprehensive_llm_prompt(
        client_input,
        available_bns_categories,
        available_interests,
        valid_warehouses_for_prompt
    )

    llm_response_dict = _invoke_comprehensive_llm(user_prompt, ai_client, model, expected_keys)

    if llm_response_dict:
        finalized_data_dict = _finalize_data_from_llm_response(
            llm_response_dict,
            client_input,
            available_bns_categories,
            available_interests,
            valid_warehouses,
            currency_conversion_rates
        )
        
        from dataclasses import asdict

        base_data = asdict(client_input)
        base_data.update(finalized_data_dict)
        return PostData(**base_data)
    else:
        raise RuntimeError("ERROR: LLM response was invalid or call failed.")

if __name__ == '__main__':
    # --- Example Usage ---
    print("--- Post Generator Example ---")

    # Dummy data for testing
    client_input = PostData(
        title="",
        content="",
        image_url="",
        category=0,
        interest="",
        warehouse="",
        item_url="https://www.lush.com/uk/en/p/wasabi-shan-kui-shampoo?queryId=a9d530215c36459b66438cd919d05285",
        item_name="",
        source_price=0.0,
        source_currency="",
        item_unit_price=0.0,
        item_weight=0.0,
        region="HK",
    )

    available_cats = [
        Category(label=label, value=i)
        for i, label in enumerate([
            "sports", "healthcare", "fashion", "home", "recipe",
            "diy", "art", "stationery", "entertainment", "vehicle",
            "electronics", "baby-care", "music", "photography",
            "beauty", "pet"
        ], 1)
    ]

    available_interests = [
        Interest(label=label, value=val)
        for label, val in [
            ("Fashion", "fashion"),
            ("Recipe", "recipe"),
            ("Photography", "photography")
        ]
    ]
    
    # warehouse, warehouse_currency_code
    warehouses = [
        Warehouse(label="", value=w_id, currency=cur)
        for w_id, cur in [
            ("warehouse-4px-uspdx", "USD"),
            ("warehouse-bnsca-toronto", "CAD"),
            ("warehouse-bnsuk-ashford", "GBP"),
            ("warehouse-bnsit-milan", "EUR"),
            ("warehouse-qs-osaka", "JPY"),
            ("warehouse-kas-seoul", "KRW"),
            ("warehouse-lht-dongguan", "CNY"),
            ("warehouse-bnstw-taipei", "TWD"),
            ("warehouse-bnsau-sydney", "AUD"),
            ("warehouse-bnsth-bangkok", "THB")
        ]
    ]

    forex_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "presets", "forex_rates.json")
    rates = load_forex_rates_from_json(forex_file)

    stub_ai_client = OpenAIClient()

    print("\n--- Generating Post for Sample Input ---")
    post1 = generate_post(
        client_input,
        available_cats,
        available_interests,
        warehouses,
        rates,
        stub_ai_client,
        "gpt-4.1-mini"
    )
    print("\n--- Final PostData ---")
    print(json.dumps(post1.__dict__, indent=2, ensure_ascii=False))