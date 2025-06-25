# modules/post_generator.py
import json
import os
from typing import Dict, List, Optional, Any, Tuple

from modules.models import PostData, Category, Warehouse, Interest
from modules.llm_client import LLMClient
from modules.openai_client import OpenAIClient
from utils.llm import extract_and_parse_json
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

# Default call-to-action text. Map keys are warehouse codes for future use.
CTA_BY_WAREHOUSE: Dict[str, str] = {
    "DEFAULT": "Shop with Buyandship today!",
}

def _append_call_to_action(content: str, warehouse_code: str) -> str:
    """Append a CTA to ``content`` based on ``warehouse_code``."""
    cta = CTA_BY_WAREHOUSE.get(warehouse_code, CTA_BY_WAREHOUSE["DEFAULT"])
    content = content.rstrip() if content else ""
    return f"{content}\n\n{cta}" if cta else content

# --- Internal Helper Functions ---

def _predict_warehouse_from_currency(
    source_currency: str,
    valid_warehouses: List[str],
    ai_client: LLMClient,
    model: str,
) -> Optional[str]:
    """Predict the best warehouse using only the currency."""
    prompt = (
        "Given the warehouse codes "
        f"{valid_warehouses}. Which warehouse is geographically closest to the "
        f"region where the currency '{source_currency}' is primarily used? "
        "Respond with JSON {\"warehouse\": \"<code>\"}."
    )
    _, raw = ai_client.get_response(prompt=prompt, model=model)

    if not raw:
        return None
    try:
        data = extract_and_parse_json(raw)
    except Exception:
        return None
    if isinstance(data, dict):
        wh = data.get("warehouse")
        if isinstance(wh, str) and wh in valid_warehouses:
            return wh
    return None

def _build_comprehensive_llm_prompt(
    item_data: PostData,
    available_bns_categories: List[Category],
    available_interests: List[Interest],
) -> Tuple[str, List[str]]:
    prompt_lines = []
    category_labels = [c.label for c in available_bns_categories]
    interest_labels = [i.label for i in available_interests]

    # --- Step-by-step workflow ---
    prompt_lines.append(
        "\n--- STEP-BY-STEP WORKFLOW ---"
        "\n1. Cleanup the item name provided by the scraper."
        "\n2. Select the most suitable category and interest from the lists above (never create new values)."
        "\n3. Generate region-specific 'title' and 'content' matching the exact structure and tone of the provided examples."
        "\n4. Output a single valid JSON object using the structure below with no commentary or markdown."
    )

    # --- Output format & guardrails ---
    prompt_lines.append("\n--- REQUIRED JSON OUTPUT STRUCTURE ---")
    prompt_lines.append(
        "Your entire response MUST be exactly one JSON object with these keys."
    )
    output_fields = ["item_name", "category", "interest", "title", "content"]
    field_desc = {
        "item_name": '  "item_name": "string"',
        "category": '  "category": "string_from_list"',
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

    prompt_lines.append("\n--- CLIENT-PROVIDED DATA & INSTRUCTIONS ---")
    prompt_lines.append(f"Item URL to analyze: {item_data.item_url}")
    prompt_lines.append(f"Target region for the post style: {item_data.region}")

    # Field-specific instructions
    # item_name
    prompt_lines.append(
        f"The scraper found the name '{item_data.item_name}'."
    )
    prompt_lines.append(
        "- Clean this up by returning only the brand and main product type. "
        "Remove redundant words, repeated descriptors, and all marketing or occasion-related text. "
        "Return only the cleaned name in the 'item_name' field."
    )


    # category (MCQ)
    prompt_lines.append(
        f"- From the following list of valid post categories: {category_labels}, select the single most appropriate category for the post. Place your choice in the 'category' field."
    )

    # interest (MCQ)
    prompt_lines.append(
        f"- From the following list of valid item categories: {interest_labels}, select the single most appropriate category for the item. Place your choice in the 'interest' field."
    )
    
    # title & content
    master_examples_list_for_region = MASTER_POST_EXAMPLES.get(item_data.region.upper())
    if not master_examples_list_for_region: # Check if the list is None or empty
        raise NotImplementedError(
            f"CRITICAL PROMPT WARNING: No master examples found for region '{item_data.region}'. "
            "ICL for title/content will not be effective."
        )
    else:
        master_examples_json_str = json.dumps(master_examples_list_for_region, ensure_ascii=False, indent=2)
        language_guidance = (
            f"Both title and content must be in the same language as these master examples for '{item_data.region}', "
            "and content should similarly match their language style."
        )

    prompt_lines.append(
        "\n--- CONTENT GENERATION (TITLE & CONTENT) ---"
        "\nBased on all information (client-provided and your findings from your search), "
        "generate 'title' (string) and 'content' (string, plain text, NO MARKDOWN formatting)."
    )
    prompt_lines.append(
        f"The style, tone, and structure for 'title' and 'content' should be closely guided by the master examples "
        f"provided below for the {item_data.region} region. {language_guidance} "
        "Your 'content' must contain two sections in this order:\n"
        "1. 'Product information' — bullet points in a formal tone describing key details.\n"
        "   - Include the expiration date if the item is food.\n"
        "   - Include available sizes if the item is clothing.\n"
        "2. 'User review summary' — bullet points in a casual tone summarizing user feedback."
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
    ai_client: LLMClient,
    model: str,
    expected_keys: List[str]

) -> Tuple[Optional[Dict[str, Any]], Any]:
    raw_response, raw_response_str = ai_client.get_response(
        prompt=user_prompt,
        model=model,
        use_search=ai_client.supports_web_search,
    )

    if raw_response_str:
        parsed_json = extract_and_parse_json(raw_response_str)
        print(f"DEBUG: Raw LLM response: {parsed_json}")
        if isinstance(parsed_json, dict):
            # Validate that all expected keys are present in LLM response
            missing_keys = [key for key in expected_keys if key not in parsed_json]
            if missing_keys:
                print(f"Warning: LLM response missing required keys: {missing_keys}. Raw: {raw_response_str}")
            return parsed_json, raw_response
        else:
            raise ValueError(f"LLM response was not a valid JSON dictionary. Raw: {raw_response_str}")
    return None, raw_response

def _parse_llm_post_fields(
    llm_output: Dict[str, Any],
    available_bns_categories: List[Category],
    available_interests: List[Interest],
) -> Dict[str, Any]:
    """Convert category/interest labels from the LLM into stored values."""
    parsed = {
        "item_name": llm_output.get("item_name"),
        "title": llm_output.get("title"),
        "content": llm_output.get("content"),
    }

    label_to_value = {c.label: c.value for c in available_bns_categories}
    parsed["category"] = label_to_value.get(llm_output.get("category"))

    label_to_interest_value = {i.label: i.value for i in available_interests}
    parsed["interest"] = label_to_interest_value.get(llm_output.get("interest"))

    return parsed


def _assemble_post_data(
    parsed_llm_fields: Dict[str, Any],
    predicted_warehouse: str,
    original_item_data: PostData,
    available_bns_categories: List[Category],
    available_interests: List[Interest],
    valid_warehouses: List[Warehouse],
    currency_conversion_rates: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    final_data = {}

    # --- Required fields from client input, passed through ---
    final_data["item_url"] = original_item_data.item_url
    final_data["region"] = original_item_data.region

    # --- Optional fields from client input, passed through ---
    final_data["user"] = original_item_data.user
    final_data["status"] = original_item_data.status
    final_data["is_pinned"] = original_item_data.is_pinned
    final_data["pinned_end_datetime"] = original_item_data.pinned_end_datetime
    final_data["pinned_expire_hours"] = original_item_data.pinned_expire_hours
    final_data["disable_comment"] = original_item_data.disable_comment
    final_data["team_id"] = original_item_data.team_id
    final_data["payment_method"] = original_item_data.payment_method
    final_data["item_weight"] = original_item_data.item_weight
    final_data["discounted"] = original_item_data.discounted

    # --- Scraper output, passed through ---
    final_data["image_url"] = original_item_data.image_url
    final_data["source_price"] = original_item_data.source_price
    final_data["source_currency"] = original_item_data.source_currency
    final_data["item_weight"] = original_item_data.item_weight

    # --- Apply LLM generated / transformed output ---
    final_data["item_name"] = parsed_llm_fields.get("item_name")
    final_data["title"] = parsed_llm_fields.get("title")
    final_data["content"] = parsed_llm_fields.get("content")

    # Validate warehouse prediction and get currency
    target_warehouse = next((wh for wh in valid_warehouses if wh.value == predicted_warehouse), None)

    if not target_warehouse:
        print("Warning: Predicted warehouse invalid or missing. Defaulting warehouse from valid list.")
        target_warehouse = valid_warehouses[0]

    final_data["warehouse"] = target_warehouse.value
    target_currency = target_warehouse.currency.upper()

    # Perform price conversion to target_currency
    source_price = final_data.get("source_price", 0.0)
    source_currency = final_data.get("source_currency", None)

    if source_price is None:
        print("Warning: Source price is None. Using 0.0 as price in target currency.")
        final_item_price_converted = 0.0
    elif source_currency is None or source_currency == "N/A":
        print("Warning: Source currency is None or 'N/A'. Using 0.0 as price in target currency.")
        final_item_price_converted = 0.0
    else:
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

    final_data["item_unit_price"] = final_item_price_converted

    # Category (convert label to numeric value)
    label_to_value = {c.label: c.value for c in available_bns_categories}
    value_to_label = {c.value: c.label for c in available_bns_categories}
    values = set(label_to_value.values())
    if original_item_data.category and original_item_data.category in values:
        final_data["category"] = original_item_data.category
    elif parsed_llm_fields.get("category") in values:
        final_data["category"] = parsed_llm_fields["category"]
    elif values:
        print(
            "Warning: Client/LLM category invalid or missing. Defaulting from valid list."
        )
        final_data["category"] = next(iter(values))

    final_data["category_label"] = value_to_label.get(final_data["category"], "")

    # Interest (convert label to value)
    label_to_interest_value = {i.label: i.value for i in available_interests}
    interest_values = set(label_to_interest_value.values())
    if original_item_data.interest and original_item_data.interest in interest_values:
        final_data["interest"] = original_item_data.interest
    elif parsed_llm_fields.get("interest") in interest_values:
        final_data["interest"] = parsed_llm_fields["interest"]
    elif interest_values:
        print(
            "Warning: Client/LLM interest invalid or missing. Defaulting from valid list."
        )
        final_data["interest"] = next(iter(interest_values))

    # Append CTA to the content based on the final warehouse
    final_data["content"] = _append_call_to_action(
        final_data.get("content", ""), final_data["warehouse"]
    )

    return final_data

# --- Public API Function ---
def generate_post(
    item_data: PostData,
    available_bns_categories: List[Category],
    available_interests: List[Interest],
    valid_warehouses: List[Warehouse],
    currency_conversion_rates: Dict[str, Dict[str, float]],
    ai_client: LLMClient,
    model: str
) -> PostData:
    print(f"INFO: Starting post generation for URL: {item_data.item_url}, Region: {item_data.region}")


    valid_warehouses_for_prompt = [wh.value for wh in valid_warehouses]

    predicted_warehouse = item_data.warehouse or _predict_warehouse_from_currency(
        item_data.source_currency,
        valid_warehouses_for_prompt,
        ai_client,
        model,
    )
    if not predicted_warehouse:
        predicted_warehouse = valid_warehouses_for_prompt[0]

    user_prompt, expected_keys = _build_comprehensive_llm_prompt(
        item_data,
        available_bns_categories,
        available_interests,
    )

    llm_response_dict, raw_llm_response = _invoke_comprehensive_llm(
        user_prompt, ai_client, model, expected_keys
    )

    if not ai_client.web_search_occurred(raw_llm_response):
        raise ValueError("LLM response indicates no web search occurred")

    if llm_response_dict:
        parsed_fields = _parse_llm_post_fields(
            llm_response_dict,
            available_bns_categories,
            available_interests,
        )

        finalized_data_dict = _assemble_post_data(
            parsed_fields,
            predicted_warehouse,
            item_data,
            available_bns_categories,
            available_interests,
            valid_warehouses,
            currency_conversion_rates,
        )
        
        from dataclasses import asdict

        base_data = asdict(item_data)
        base_data.update(finalized_data_dict)
        return PostData(**base_data)
    else:
        raise RuntimeError("ERROR: LLM response was invalid or call failed.")

if __name__ == '__main__':
    # --- Example Usage ---
    print("--- Post Generator Example ---")

    # Dummy data for testing
    item_data = PostData(
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
        item_data,
        available_cats,
        available_interests,
        warehouses,
        rates,
        stub_ai_client,
        "gpt-4.1-mini"
    )
    print("\n--- Final PostData ---")
    print(json.dumps(post1.__dict__, indent=2, ensure_ascii=False))