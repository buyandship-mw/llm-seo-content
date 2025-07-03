# modules/post_generator.py
import json
import os
from typing import Dict, List, Optional, Any, Tuple

from modules.core.models import PostData, Category, Warehouse, Interest
from modules.clients.llm_client import LLMClient
from modules.clients.openai_client import OpenAIClient
from utils.llm import extract_and_parse_json
from modules.io.csv_parser import load_forex_rates_from_json
from utils.currency import convert_price

# --- Module Constants ---
MASTER_POST_EXAMPLES: Dict[str, List[Dict[str, str]]] = {
    "HK": [
        {
            "item_url": "https://www.target.com/p/fujifilm-instax-mini-12-camera/-/A-88743864",
            "item_name": "Fujifilm Instax Mini 12 Camera",
            "title": "📸 Fujifilm Instax Mini 12 | 即影即有，輕鬆記錄生活點滴",
            "content":
                """
想隨時隨地用相片捕捉生活嘅美好時刻？
• 自動曝光功能，無論光暗環境，一按即拍出清晰靚相。
• 近拍模式升級，影美食、小物特寫，細節都睇得一清二楚。
• 內置自拍鏡，同朋友 selfie 構圖更方便，唔再怕影到半邊面。
• 5 秒高速打印，歡樂即時分享，絕對係派對必備！

超過 10,000+ 用家 ⭐4.7/5 好評，公認「新手最易用嘅即影即有相機」。
【美國 Target 正貨】
                """
        },
        {
            "item_url": "https://www.standoil.kr/product/detail.html?product_no=719&cate_no=543&display_group=1",
            "item_name": "Standoil More Baguette Bag",
            "title": "👜 Standoil More Baguette Bag | 韓國小眾設計，日常百搭之選",
            "content":
                """
搵緊一個返工、放假都啱用嘅手袋？
• 採用光澤感人造皮革，觸感柔軟又易打理，落雨都唔驚。
• 容量充足，輕鬆收納銀包、電話、化妝品等日常必備品。
• 內附拉鍊暗格及雙開口袋，方便分類收納，告別大海撈針。
• 簡約法棍包型，設計經典，輕鬆配襯任何 OOTD。

韓國女生人手一個，官網經常斷貨嘅人氣款式！
【韓國官網直送】
                """
        },
        {
            "item_url": "https://www.lush.com/uk/en/p/wasabi-shan-kui-shampoo",
            "item_name": "Lush Wasabi Shan Kui Shampoo",
            "title": "🌿 Lush Wasabi Shan Kui Shampoo | 喚醒頭皮，重現豐盈感",
            "content":
                """
覺得頭髮扁塌、冇生氣？想搵返清爽嘅頭皮感覺？
• 獨特山葵、辣根成分，有效刺激頭皮，促進頭髮健康生長。
• 海鹽同公平貿易橄欖油，溫和潔淨同時深層滋潤，髮絲更顯光澤。
• 薄荷腦同柑橘精油，帶來清新冰涼感，洗後成個人都精神晒。
• 適合追求頭髮豐盈感、關注頭皮健康嘅你。

唔少用家評價「用完頭皮好爽，頭髮明顯蓬鬆咗」。
【英國 LUSH 手工製造】
                """
        }
    ]
}

# Preferred language for item_name and title by region
PREFERRED_LANG_BY_REGION: Dict[str, str] = {
    "HK": "English",
}

# Default call-to-action text. Map keys are warehouse codes for future use.
CTA_BY_WAREHOUSE: Dict[str, str] = {
    "DEFAULT": (
        "想入手{item_name}香港未必有？ 想知道{item_name} 怎樣買？\n"
        "立即在{country}網站下單，{weight_blurb}透過 Buy&Ship 運回香港，立即建立代購訂單！"
    ),
}

# Mapping of warehouse code to its corresponding country/region name in Chinese
COUNTRY_BY_WAREHOUSE: Dict[str, str] = {
    "warehouse-4px-uspdx": "美國",
    "warehouse-bnsus-la": "美國",
    "warehouse-bnsca-toronto": "加拿大",
    "warehouse-bnsuk-ashford": "英國",
    "warehouse-bnsit-milan": "意大利",
    "warehouse-qs-osaka": "日本",
    "warehouse-bnsjp-2": "日本",
    "warehouse-kas-seoul": "韓國",
    "warehouse-lht-dongguan": "中國",
    "warehouse-bns-hk": "香港",
    "warehouse-bnstw-taipei": "台灣",
    "warehouse-bnsau-sydney": "澳洲",
    "warehouse-bnsth-bangkok": "泰國",
    "warehouse-bnsid-jakarta": "印尼",
}

def _append_call_to_action(
    content: str,
    warehouse_code: str,
    item_name: str,
    item_weight: Optional[float] = None,
) -> str:
    """Append a CTA to ``content`` based on ``warehouse_code`` and ``item_weight``."""
    cta_template = CTA_BY_WAREHOUSE.get(warehouse_code, CTA_BY_WAREHOUSE["DEFAULT"])
    country = COUNTRY_BY_WAREHOUSE.get(warehouse_code, "")

    weight_blurb = ""
    if item_weight:
        pounds = round(item_weight / 453.59237, 2)
        weight_blurb = f"大約{pounds}磅，"

    cta = cta_template.format(
        weight_blurb=weight_blurb, item_name=item_name, country=country
    )
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

    # --- REVISED: Step-by-step workflow for persona-derivation ---
    prompt_lines.append(
        (
            "\n--- YOUR MISSION & STEP-BY-STEP WORKFLOW ---"
            "\nYou are an expert e-commerce copywriter specializing in SEO and direct response for the Hong Kong market."
            "\nYour mission is to generate a compelling, persona-driven product post."
            "\nFollow this internal thought process precisely:"
            "\n"
            "\n**Part 1: Internal Analysis (Do not include in final JSON output)**"
            "\n1.  **Analyze Product:** Access the `item_url` to understand the product's features, benefits, and user reviews."
            "\n2.  **Define Buyer Persona:** Based on the product and target region ('{region}'), internally define the primary buyer persona. Ask yourself: Who are they? What do they value? (e.g., 'A tech-savvy student who values portability and battery life' or 'A new parent prioritizing safety and ease of use')."
            "\n3.  **Formulate Copy Strategy:** Based on the persona, internally formulate a specific angle for the AIDA copy framework. Determine the main hook (Attention), key benefits (Interest), and strongest social proof (Desire)."
            "\n"
            "\n**Part 2: Execute and Generate JSON Output**"
            "\nAfter completing your internal analysis, execute the following tasks and provide the output *only* in the required JSON structure below, with no commentary or markdown."
        ).format(region=item_data.region)
    )

    # --- REQUIRED JSON OUTPUT STRUCTURE (No changes needed here) ---
    prompt_lines.append("\n--- REQUIRED JSON OUTPUT STRUCTURE ---")
    prompt_lines.append(
        "Your entire response MUST be exactly one JSON object with these keys."
    )
    output_fields = [
        "item_name",
        "brand_name",
        "category",
        "interest",
        "title",
        "content",
    ]
    field_desc = {
        "item_name": '  "item_name": "string"',
        "brand_name": '  "brand_name": "string"',
        "category": '  "category": "string_from_list"',
        "interest": '  "interest": "string_from_list"',
        "source_currency": '  "source_currency": "3_letter_code_or_\\"N/A\\""',
        "source_price": '  "source_price": "float"',
        "title": '  "title": "string"',
        "content": '  "content": "string_plain_text"',
        "item_weight": '  "item_weight": "float_or_null"',
    }
    output_lines = ["{\n"]
    output_fields_with_desc = [
        "item_name",
        "brand_name",
        "category",
        "interest",
        "title",
        "content",
    ]
    for idx, key in enumerate(output_fields_with_desc):
        comma = "," if idx < len(output_fields_with_desc) - 1 else ""
        output_lines.append(f"{field_desc[key]}{comma}\n")
    output_lines.append("}")
    prompt_lines.append("".join(output_lines))

    # --- REVISED: Streamlined client data and instructions ---
    prompt_lines.append("\n--- CLIENT-PROVIDED DATA & INSTRUCTIONS ---")
    prompt_lines.append(f"Item URL to analyze: {item_data.item_url}")
    prompt_lines.append(f"Target region for the post style: {item_data.region}")
    prompt_lines.append(f"The scraper found this initial item name: {item_data.item_name}.")
    prompt_lines.append(
        "\n--- FIELD-SPECIFIC TASKS ---"
        "\n- `item_name` & `brand_name`: Based on your analysis, clean the item name (keep only brand and model, max 6-8 words) and extract the `brand_name`."
        f"\n- `category`: From the list `{category_labels}`, select the single best category."
        f"\n- `interest`: From the list `{interest_labels}`, select the single best interest."
        "\n- `title` & `content`: Generate these using the persona and copy strategy you defined in Part 1. The `content` must strictly follow the AIDA model."
    )

    # --- REVISED: More direct content generation instructions ---
    master_examples_list_for_region = MASTER_POST_EXAMPLES.get(item_data.region.upper())
    if not master_examples_list_for_region:
        raise NotImplementedError(
            f"CRITICAL PROMPT WARNING: No master examples for region '{item_data.region}'."
        )

    master_examples_json_str = json.dumps(master_examples_list_for_region, ensure_ascii=False, indent=2)

    prompt_lines.append(
        "\n--- CONTENT GENERATION (TITLE & CONTENT) ---\n"
        "Remember the persona you defined. Now, generate:\n"
        "  • `title` (string, max 60 chars): Prepend a relevant emoji. Write a benefit-driven title that speaks to your persona.\n"
        "  • `content` (string, 110-150 words, plain text):\n"
        "    Use the AIDA-SEO model precisely:\n"
        "    - **Attention (Hook):** 1 sentence targeting the core desire/pain of your persona.\n"
        "    - **Interest (Benefits):** 3-4 bullet points (using '•') that translate features into benefits your persona cares about.\n"
        "    - **Desire (Social Proof):** 1-2 lines of social proof (reviews, ratings) or trust signals (authenticity) that resonate with your persona.\n"
        "    - **Action (CTA):** You do not need to write the CTA. It will be appended automatically."
    )

    prompt_lines.append(
        f"\n--- GOLD-STANDARD EXAMPLES ---"
        f"\nThese examples show the desired structure, tone, and AIDA format. Learn from them:\n"
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
    if not ai_client.supports_web_search:
        raise ValueError("LLM client does not support web search, cannot proceed.")
    
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
        "brand_name": llm_output.get("brand_name"),
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
    final_data["brand_name"] = parsed_llm_fields.get("brand_name")
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
    source_price = final_data.get("source_price")
    source_currency = final_data.get("source_currency")

    if source_price in (None, 0, 0.0):
        raise ValueError("Source price is missing or zero, cannot generate post")
    if source_currency is None or source_currency in ("", "N/A"):
        raise ValueError("Source currency is missing, cannot generate post")

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
            raise ValueError(
                f"Conversion failed from {source_currency} to {target_currency}"
            )

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

    # Append CTA to the content based on the final warehouse and item name
    final_data["content"] = _append_call_to_action(
        final_data.get("content", ""),
        final_data["warehouse"],
        final_data.get("item_name", ""),
        final_data.get("item_weight"),
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