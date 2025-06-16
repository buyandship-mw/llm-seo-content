# modules/post_generator.py
import json
from typing import Dict, List, Optional, Any, Tuple

from modules.models import PostData, Category, Warehouse
from modules.openai_client import OpenAIClient, extract_and_parse_json # Using your client

# --- Module Constants ---
MASTER_POST_EXAMPLES: Dict[str, List[Dict[str, str]]] = {
    "HK": [{
        "item_url": "https://www.target.com/p/fujifilm-instax-mini-12-camera/-/A-88743864",
        "item_name": "Fujifilm Instax Mini 12 Camera",
        "warehouse": "warehouse-4px-uspdx",
        "post_title": "📸 Fujifilm Instax Mini 12",
        "post_content":
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
        "post_title": "🎧 Chiikawa 完全無線立體聲耳機",
        "post_content":
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

def _get_conversion_rate(
    from_currency: str,
    to_currency: str,
    rates_table: Dict[str, Dict[str, float]]
) -> Optional[float]:
    """Helper to get conversion rate from the provided table."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0
    if from_currency in rates_table and to_currency in rates_table[from_currency]:
        return rates_table[from_currency][to_currency]
    
    # Try inverse if direct not found (e.g., table has USD:EUR but we need EUR:USD)
    if to_currency in rates_table and from_currency in rates_table[to_currency]:
        inverse_rate = rates_table[to_currency][from_currency]
        if inverse_rate != 0: # Avoid division by zero
            return 1.0 / inverse_rate
            
    print(f"Warning: Conversion rate from {from_currency} to {to_currency} not found in table.")
    return None


def _build_comprehensive_llm_prompt(
    client_input: PostData,
    available_bns_categories: List[Category],
    valid_warehouses_for_mcq: List[str]  # Just the warehouse codes for the prompt
) -> str:
    prompt_lines = []
    category_labels = [c.label for c in available_bns_categories]

    # 1. Role Definition & Overall Goal
    prompt_lines.append(
        "You are an expert e-commerce data processor and content creator. "
        "Your goal is to analyze client-provided data, search the item_url "
        "for missing details or verifications, make specified predictions from lists, "
        "and generate post content. All generated textual content should be appropriate for the target region specified. " # Added subtle hint
        "Output everything in a single, specific JSON structure."
    )
    prompt_lines.append("\n--- REQUIRED JSON OUTPUT STRUCTURE ---")
    prompt_lines.append(
        "Your entire response MUST be a single JSON object with the following exact keys "
        "and value types (use null for optional string fields if no relevant information is found, "
        "unless specified otherwise, ensure price is a float and currency a 3-letter code):\n"
        "{\n"
        '  "item_name": "string", // Should be in the primary language of the target post region\n' # Added comment
        '  "image_url": "string_url | null",\n'
        '  "post_category": "string_chosen_from_provided_list",\n'
        '  "warehouse": "string_chosen_from_provided_list_or_clients_value",\n'
        '  "item_currency": "string_3_letter_code_as_found_on_site",\n'
        '  "item_price_in_item_currency": "float_as_found_on_site",\n'
        '  "post_title": "string", // Should be in the primary language of the target post region\n' # Added comment
        '  "post_content": "string_plain_text_no_markdown" // Should be in the primary language of the target post region\n' # Added comment
        "}"
    )
    prompt_lines.append("\n--- CLIENT-PROVIDED DATA & INSTRUCTIONS ---")
    prompt_lines.append(f"Item URL to analyze: {client_input.item_url}")
    prompt_lines.append(f"Target region for the post style: {client_input.region}")

    # Field-specific instructions
    # item_name
    if client_input.item_name:
        prompt_lines.append(f"- Use '{client_input.item_name}' for the 'item_name' field in your JSON output.")
    else:
        prompt_lines.append(f"- Determine the item's name from '{client_input.item_url}'. If not already, translate this name to English. Place the result in the 'item_name' field.")

    # image_url
    if client_input.image_url:
        prompt_lines.append(f"- Use '{client_input.image_url}' for the 'image_url' field in your JSON output.")
    else:
        prompt_lines.append(
            f"- Perform a web search for the item at the provided item_url and find the best image URL. "
            "Place this definitive URL in the 'image_url' field. If no suitable image is found, use null."
        )

    # warehouse (MCQ)
    if client_input.warehouse:
        prompt_lines.append(f"- Use '{client_input.warehouse}' for the 'warehouse' field in your JSON output.")
    else:
        prompt_lines.append(
            f"- Determine the primary country this item is sold from via web search on {client_input.item_url}."
        )
        prompt_lines.append(
            f"- Then, from the following list of valid warehouses: {valid_warehouses_for_mcq}, select the one whose country is the same as or geographically closest to the country the item is sold from. Place your choice in the 'warehouse' field."
        )

    # post_category (MCQ)
    if client_input.category:
        existing_label = next(
            (c.label for c in available_bns_categories if c.value == client_input.category),
            None,
        )
        if existing_label:
            prompt_lines.append(
                f"- Use '{existing_label}' for the 'post_category' field in your JSON output."
            )
        else:
            prompt_lines.append(
                f"- From the following list of valid BNS Post Categories: {category_labels}, select the single most appropriate category for the item based on all its details. Place your choice in the 'post_category' field."
            )
    else:
        prompt_lines.append(
            f"- From the following list of valid BNS Post Categories: {category_labels}, select the single most appropriate category for the item based on all its details. Place your choice in the 'post_category' field."
        )

    # item_currency & item_price_in_item_currency
    prompt_lines.append(
        f"- Determine the item's price from '{client_input.item_url}'. Extract the numeric price value and its currency. "
        "Convert the currency to its standard three-letter code (e.g., USD, EUR, JPY). "
        "Place the numeric price as a float in 'item_price_in_item_currency' and the 3-letter currency code in 'item_currency'. "
        "If price is not found, use 0.0 for price and 'N/A' for currency."
    )
    
    # post_title & post_content
    master_examples_list_for_region = MASTER_POST_EXAMPLES.get(client_input.region.upper())
    if not master_examples_list_for_region: # Check if the list is None or empty
        raise NotImplementedError(
            f"CRITICAL PROMPT WARNING: No master examples found for region '{client_input.region}'. "
            "ICL for title/content will not be effective."
        )
    else:
        # Convert the list of example dictionaries into a JSON string.
        # This will result in a JSON array of objects.
        master_examples_json_str = json.dumps(master_examples_list_for_region, ensure_ascii=False, indent=2)
        
        # Update language guidance to refer to plural examples
        language_guidance = (
            f"Generate the 'post_title' and 'post_content' directly in the primary language "
            f"of the target region ('{client_input.region}'), matching the language style, tone, "
            f"and structure demonstrated in the provided master examples."
        )

    prompt_lines.append(
        "\n--- CONTENT GENERATION (TITLE & CONTENT) ---" # Updated section title for clarity
        f"\nBased on all information (client-provided and your findings from web search), "
        "generate 'post_title' (string) and 'post_content' (string, plain text, NO MARKDOWN formatting)."
    )
    prompt_lines.append(
        # Updated wording to refer to "examples" (plural)
        f"The style, tone, and structure for 'post_title' and 'post_content' should be closely guided by the master examples "
        f"provided below for the {client_input.region} region. "
        f"{language_guidance} " # language_guidance already refers to plural examples
        f"The 'post_content' should generally have two main sections based on your web search: "
        "1. a product introduction (highlighting key features/benefits), and "
        "2. a brief summary of user reviews or public sentiment."
    )
    prompt_lines.append(
        # Updated introductory phrase for the examples
        f"Here are some master examples for your reference. Learn from their structure, "
        f"item details they choose to highlight, and how they phrase the title and content sections:\n"
        f"{master_examples_json_str}"
    )

    return "\n\n".join(prompt_lines)

def _invoke_comprehensive_llm(
    user_prompt: str,
    ai_client: OpenAIClient,
    model: str
) -> Optional[Dict[str, Any]]:
    messages = [{"role": "user", "content": user_prompt}]
    raw_response_str = ai_client.get_completion_with_search(model=model, messages=messages)

    if raw_response_str:
        parsed_json = extract_and_parse_json(raw_response_str)
        print(f"DEBUG: Raw LLM response: {parsed_json}")
        if isinstance(parsed_json, dict):
            # Validate that all required keys are present in LLM response
            required_keys = [
                "item_name", "image_url", "post_category", "warehouse",
                "item_currency", "item_price_in_item_currency",
                "post_title", "post_content"
            ]
            missing_keys = [key for key in required_keys if key not in parsed_json]
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
    valid_warehouses: List[Warehouse],
    currency_conversion_rates: Dict[str, Dict[str, float]]
) -> Dict[str, Any]:
    final_data = {}

    # --- Populate with defaults first, to ensure all keys exist ---
    # These are for PostData object, which has more fields than LLM output
    final_data["item_name"] = "Item Name Unavailable"
    final_data["image_url"] = DEFAULT_FALLBACK_IMAGE_URL
    category_labels = [c.label for c in available_bns_categories]
    warehouse_codes_only = [w.value for w in valid_warehouses]

    final_data["category"] = (
        category_labels[0] if category_labels else 0
    )
    final_data["warehouse"] = (
        warehouse_codes_only[0] if warehouse_codes_only else "UNKNOWN_WAREHOUSE"
    )
    final_data["item_unit_price"] = 0.0
    final_data["title"] = "Title Generation Failed"
    final_data["content"] = "Content Generation Failed. Please check item URL."

    # Optional fields from client input, passed through
    final_data["discounted"] = original_client_input.discounted
    final_data["item_weight"] = original_client_input.item_weight
    final_data["payment_method"] = original_client_input.payment_method

    # --- Apply LLM output and client overrides ---

    # 1. item_name
    if original_client_input.item_name:
        final_data["item_name"] = original_client_input.item_name
    elif llm_output.get("item_name"):
        final_data["item_name"] = str(llm_output.get("item_name"))

    # 2. image_url (Prefer LLM's finding)
    if llm_output.get("image_url"):
        final_data["image_url"] = str(llm_output.get("image_url"))
    elif original_client_input.image_url: # Fallback to client's if LLM provides none
        final_data["image_url"] = original_client_input.image_url
    # else it keeps DEFAULT_FALLBACK_IMAGE_URL

    # 3. warehouse & target_warehouse_currency
    valid_warehouse_codes_only = warehouse_codes_only
    target_warehouse_currency = "N/A"

    if (
        original_client_input.warehouse
        and original_client_input.warehouse in valid_warehouse_codes_only
    ):
        final_data["warehouse"] = original_client_input.warehouse
    elif "warehouse" in llm_output and llm_output["warehouse"] in valid_warehouse_codes_only:
        final_data["warehouse"] = str(llm_output["warehouse"])
    elif valid_warehouse_codes_only: # Default to first valid if others fail
        print(
            f"Warning: Client/LLM warehouse invalid or missing. Defaulting from valid list."
        )
        final_data["warehouse"] = valid_warehouse_codes_only[0]
    # else it keeps "UNKNOWN_WAREHOUSE" (or previous default)

    # Find currency for the chosen warehouse
    for wh in valid_warehouses:
        if wh.value == final_data["warehouse"]:
            target_warehouse_currency = wh.currency.upper()
            break

    if target_warehouse_currency == "N/A" and valid_warehouses:
        target_warehouse_currency = valid_warehouses[0].currency.upper()
        print(f"Warning: Could not determine target warehouse currency reliably, defaulting to {target_warehouse_currency}")


    # 4. category (convert label to numeric value)
    label_to_value = {c.label: c.value for c in available_bns_categories}
    values = set(label_to_value.values())
    if original_client_input.category and original_client_input.category in values:
        final_data["category"] = original_client_input.category
    elif "post_category" in llm_output and llm_output["post_category"] in label_to_value:
        final_data["category"] = label_to_value[llm_output["post_category"]]
    elif values:
        print(
            "Warning: Client/LLM post_category invalid or missing. Defaulting from valid list."
        )
        final_data["category"] = next(iter(values))

    # 5. Determine source_price and source_currency (from LLM)
    llm_price_val = llm_output.get("item_price_in_item_currency")
    llm_currency_val = llm_output.get("item_currency")

    source_price: Optional[float] = None
    source_currency: Optional[str] = None  # Currency as found on site

    if isinstance(llm_price_val, (float, int)) and isinstance(llm_currency_val, str) and len(llm_currency_val) == 3:
        source_price = float(llm_price_val)
        source_currency = llm_currency_val.upper()
    else:
        print(
            f"Warning: Valid source price/currency not found from LLM. LLM provided price: '{llm_price_val}', currency: '{llm_currency_val}'."
        )

    # 6. Perform Price Conversion to target_warehouse_currency
    final_item_price_converted = 0.0  # Default price

    if source_price is not None and source_currency and target_warehouse_currency not in ["N/A", None]:
        if source_currency == target_warehouse_currency:
            final_item_price_converted = source_price
        else:
            rate = _get_conversion_rate(source_currency, target_warehouse_currency, currency_conversion_rates)
            if rate is not None:
                final_item_price_converted = round(source_price * rate, 2)
            else:
                print(
                    f"Warning: Conversion failed from {source_currency} to {target_warehouse_currency}. Using 0.0."
                )
                final_item_price_converted = 0.0
    else:
        print(
            f"Warning: Target warehouse currency is '{target_warehouse_currency}'. Using 0.0 as price in target currency."
        )
        final_item_price_converted = 0.0

    final_data["item_unit_price"] = final_item_price_converted


    # 7. post_title & post_content from LLM
    if llm_output.get("post_title"):
        final_data["title"] = str(llm_output.get("post_title"))
    if llm_output.get("post_content"):
        final_data["content"] = str(llm_output.get("post_content"))

    return final_data


# --- Public API Function ---
def generate_post(
    client_input: PostData,
    available_bns_categories: List[Category],
    valid_warehouses: List[Warehouse],
    currency_conversion_rates: Dict[str, Dict[str, float]],
    ai_client: OpenAIClient,
    model: str
) -> PostData:
    print(f"INFO: Starting post generation for URL: {client_input.item_url}, Region: {client_input.region}")

    valid_warehouses_for_prompt = [wh.value for wh in valid_warehouses]

    user_prompt = _build_comprehensive_llm_prompt(
        client_input,
        available_bns_categories,
        valid_warehouses_for_prompt
    )

    llm_response_dict = _invoke_comprehensive_llm(user_prompt, ai_client, model)

    if llm_response_dict:
        finalized_data_dict = _finalize_data_from_llm_response(
            llm_response_dict,
            client_input,
            available_bns_categories,
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

    # Simplified conversion rates
    rates = {
        "USD": {"GBP": 0.80, "EUR": 0.92, "HKD": 7.80, "USD": 1.0},
        "GBP": {"USD": 1.25, "EUR": 1.15, "HKD": 9.75, "GBP": 1.0},
        "EUR": {"USD": 1.08, "GBP": 0.87, "HKD": 8.45, "EUR": 1.0},
        "HKD": {"USD": 0.13, "GBP": 0.10, "EUR": 0.12, "HKD": 1.0},
        "JPY": {"USD": 0.007, "GBP": 0.0056, "EUR": 0.0065, "JPY": 1.0},
    }

    stub_ai_client = OpenAIClient()

    print("\n--- Generating Post for Sample Input ---")
    post1 = generate_post(client_input, available_cats, warehouses, rates, stub_ai_client, "gpt-4.1-mini")
    print("\n--- Final PostData ---")
    print(json.dumps(post1.__dict__, indent=2, ensure_ascii=False))