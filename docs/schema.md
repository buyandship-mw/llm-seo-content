Sample (demos) data schema:
- post_id
- item_category
- category (multiple choice)
- discount | null
- item_name
- item_unit_price (in purchased currency)
- item_unit_price_local (use BNS endpoint to back-compute during processing - https://b4u-req-api.buynship.com/api/bns/pricing/warehouse_currency/<region>)
- item_url
- payment_method | null
- site (shipment location)
- warehouse_id (used to compute item_unit_price_local)
- warehouse_location
- item_weight
- region (extracted from URL)
- title
- content
- hashtags | null
- like_count

Input data schema:
- item_category
- discount | null
- item_name
- item_unit_price
- item_unit_price_local
- item_url
- payment_method | null
- site
- warehouse_id
- warehouse_location
- item_weight
- region
- url_extracted_text

Output data schema:
- category (multiple choice)
- title
- content
- hashtags | null

Post data schema:
- item_category
- category (multiple choice)
- discount | null
- item_name
- item_unit_price (USD)
- item_url
- payment_method | null
- site (shipment location)
- warehouse_id
- warehouse_location
- item_weight
- region (extracted from URL)
- title
- content
- hashtags | null