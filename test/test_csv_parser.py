# test/test_csv_parser.py
import pytest
import io

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.models import InputData
from modules.csv_parser import parse_csv_to_input_data

# Helper to create CSV content as a string
def create_csv_string(headers: list[str], rows: list[list[str]]) -> str:
    header_line = ",".join(headers)
    row_lines = [".".join(row) for row in rows] # Using . as delimiter, oops, should be ,
    row_lines = [",".join(str(field) for field in row) for row in rows]
    return header_line + "\n" + "\n".join(row_lines) if rows else header_line

# Test cases
def test_parse_empty_csv(capsys):
    csv_content = "" # Completely empty
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    assert result == []

def test_parse_header_only_csv():
    csv_content = "region,item_url,item_name"
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    assert result == []

def test_parse_valid_csv_full_data():
    csv_content = (
        "region,item_url,item_name,post_category,image_url,warehouse_id,item_currency,item_price,discount,item_category,item_weight,payment_method,site\n"
        "US,http://a.com,Name1,Cat1,http://img.com/1,WH1,USD,10.99,0.5,ItemCat1,1.5,Credit,SiteA\n"
        "CA,http://b.com,Name2,Cat2,http://img.com/2,WH2,CAD,20.50,PROMO10,ItemCat2,2.0,Debit,SiteB"
    )
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    
    assert len(result) == 2
    assert result[0] == InputData(
        region="US", item_url="http://a.com", item_name="Name1", post_category="Cat1",
        image_url="http://img.com/1", warehouse_id="WH1", item_currency="USD",
        item_price=10.99, discount=0.5, item_category="ItemCat1", item_weight=1.5,
        payment_method="Credit", site="SiteA"
    )
    assert result[1] == InputData(
        region="CA", item_url="http://b.com", item_name="Name2", post_category="Cat2",
        image_url="http://img.com/2", warehouse_id="WH2", item_currency="CAD",
        item_price=20.50, discount="PROMO10", item_category="ItemCat2", item_weight=2.0,
        payment_method="Debit", site="SiteB"
    )

def test_parse_valid_csv_minimal_data():
    csv_content = (
        "region,item_url\n"
        "US,http://c.com\n"
        "GB,http://d.com"
    )
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    
    assert len(result) == 2
    assert result[0] == InputData(region="US", item_url="http://c.com")
    assert result[1] == InputData(region="GB", item_url="http://d.com")

def test_parse_csv_with_empty_optional_fields():
    csv_content = (
        "region,item_url,item_name,item_price,site\n"
        "US,http://e.com,,,\n" # item_name, item_price, site are empty
    )
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    
    assert len(result) == 1
    assert result[0] == InputData(
        region="US", item_url="http://e.com", item_name=None, item_price=None, site=None
    )

def test_missing_required_header():
    csv_content = "item_url,item_name\nhttp://f.com,NameF" # Missing 'region'
    string_io_csv = io.StringIO(csv_content)
    with pytest.raises(ValueError) as excinfo:
        parse_csv_to_input_data(string_io_csv)
    assert "CSV is missing required headers: region" in str(excinfo.value)

def test_row_missing_required_value(capsys):
    csv_content = (
        "region,item_url\n"
        ",http://g.com\n" # region is empty
        "US,\n"           # item_url is empty
        "JP,http://h.com" # valid row
    )
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    
    assert len(result) == 1 # Only the valid row should be parsed
    assert result[0].region == "JP"

def test_type_conversion_errors_for_floats(capsys):
    csv_content = (
        "region,item_url,item_price,item_weight\n"
        "US,http://i.com,not_a_price,also_not_weight\n"
        "CA,http://j.com,12.34,5.67" # valid row for comparison
    )
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    
    assert len(result) == 2
    assert result[0].item_price is None
    assert result[0].item_weight is None
    assert result[1].item_price == 12.34
    assert result[1].item_weight == 5.67

def test_discount_field_variations():
    csv_content = (
        "region,item_url,discount\n"
        "US,http://k.com,15.5\n"      # Float discount
        "CA,http://l.com,SAVE20\n"    # String discount
        "GB,http://m.com,\n"          # Empty discount (None)
        "AU,http://n.com,10\n"        # Integer-like float discount
    )
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    
    assert len(result) == 4
    assert result[0].discount == 15.5
    assert isinstance(result[0].discount, float)
    assert result[1].discount == "SAVE20"
    assert isinstance(result[1].discount, str)
    assert result[2].discount is None
    assert result[3].discount == 10.0
    assert isinstance(result[3].discount, float)

def test_spaces_and_quotes_in_csv():
    # csv.DictReader handles standard quoting and internal commas.
    # The get_cleaned_value helper handles stripping leading/trailing spaces from values.
    csv_content = (
        'region,item_url,item_name,site\n'
        '  US  , "http://example.com/path?q=value,more" , "  Spaced Name  " , Site X \n'
    )
    string_io_csv = io.StringIO(csv_content)
    result = parse_csv_to_input_data(string_io_csv)
    
    assert len(result) == 1
    assert result[0].region == "US" # Stripped by parser
    assert result[0].item_url == "http://example.com/path?q=value,more" # Not stripped by get_cleaned_value as it's inside, handled by DictReader
    assert result[0].item_name == "Spaced Name" # Stripped
    assert result[0].site == "Site X" # Stripped

@pytest.fixture
def temp_csv_file(tmp_path):
    file_path = tmp_path / "test_data.csv"
    def _create_temp_csv(content):
        file_path.write_text(content, encoding='utf-8')
        return str(file_path)
    return _create_temp_csv

def test_parse_from_file_path(temp_csv_file):
    csv_content = (
        "region,item_url,item_name\n"
        "FR,http://fr.com,French Item"
    )
    file_path = temp_csv_file(csv_content)
    result = parse_csv_to_input_data(file_path)
    
    assert len(result) == 1
    assert result[0] == InputData(region="FR", item_url="http://fr.com", item_name="French Item")