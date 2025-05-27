Sample (demos) data schema:
- item_category
- category
- discount | null
- item_name
- item_unit_price (USD)
- item_url
- payment_method
- site (shipment location)
- warehouse
- item_weight
- region
- title
- content
- hashtags | null
- media (item photos)

Input data schema:
- item_category
- discount | null
- item_name
- item_unit_price (USD)
- item_unit_price_local (calculate via region)
- item_url
- payment_method
- site (shipment location)
- warehouse
- item_weight
- region
- media (item photos)
- url_extracted_text

Output data schema:
- category
- title
- content
- hashtags | null