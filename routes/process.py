from dataclasses import asdict
from flask import Blueprint, request, jsonify

from modules.models import PostData, Category, Interest, Warehouse
from modules.post_data_builder import PostDataBuilder
from modules.openai_client import OpenAIClient
from services.executor_service import process_batch_input_data

bp = Blueprint('process', __name__)

@bp.route('/process', methods=['POST'])
def process_batch():
    """Process a batch of input data using the LLM pipeline.

    The request JSON should contain the keys ``input_data``, ``categories``,
    ``interests``, ``warehouses`` and ``rates``. Each should map to a list or
    object matching the respective dataclass structure. The endpoint returns a
    JSON list of generated ``PostData`` objects.
    """
    payload = request.get_json(silent=True) or {}

    try:
        input_list = [
            PostDataBuilder.from_dict(item).build()
            for item in payload.get('input_data', [])
        ]
        categories = [Category(**c) for c in payload.get('categories', [])]
        interests = [Interest(**i) for i in payload.get('interests', [])]
        warehouses = [Warehouse(**w) for w in payload.get('warehouses', [])]
        rates = payload.get('rates', {})
    except Exception as exc:
        return jsonify({'error': f'Invalid payload: {exc}'}), 400

    ai_client = OpenAIClient()
    results = process_batch_input_data(
        input_data_list=input_list,
        available_categories=categories,
        available_interests=interests,
        warehouses=warehouses,
        rates=rates,
        ai_client=ai_client,
    )

    return jsonify([asdict(res) for res in results])
