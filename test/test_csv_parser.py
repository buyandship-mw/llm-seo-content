import io
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.models import PostData
from modules.csv_parser import parse_csv_to_post_data
from modules.post_data_builder import PostDataBuilder


def test_parse_empty_csv():
    csv_content = ""
    result = parse_csv_to_post_data(io.StringIO(csv_content))
    assert result == []


def test_parse_header_only_csv():
    csv_content = "item_url,title"
    with pytest.raises(ValueError):
        parse_csv_to_post_data(io.StringIO(csv_content))


def test_parse_full_row():
    csv_content = (
        "item_url,region,title,content,image_url,category,interest,warehouse,item_name,source_price,source_currency,item_unit_price,item_weight\n"
        "http://a.com,US,Title A,Content A,http://img/a.jpg,1,Tech,WH1,Item A,9.99,USD,8.88,1.5"
    )
    result = parse_csv_to_post_data(io.StringIO(csv_content))
    assert len(result) == 1
    assert isinstance(result[0], PostDataBuilder)
    assert result[0].build() == PostData(
        title="Title A",
        content="Content A",
        image_url="http://img/a.jpg",
        category=1,
        category_label="",
        interest="Tech",
        warehouse="WH1",
        item_url="http://a.com",
        item_name="Item A",
        source_price=9.99,
        source_currency="USD",
        item_unit_price=8.88,
        item_weight=1.5,
        region="US",
    )


def test_parse_from_file(tmp_path):
    csv_content = (
        "item_url,region,title,content,image_url,category,interest,warehouse,item_name,source_price,source_currency,item_unit_price,item_weight\n"
        "http://b.com,CA,Title B,Content B,http://img/b.jpg,2,Food,WH2,Item B,5.5,CAD,5.5,0.3"
    )
    file_path = tmp_path / "data.csv"
    file_path.write_text(csv_content)
    result = parse_csv_to_post_data(str(file_path))
    assert len(result) == 1
    builder = result[0]
    assert isinstance(builder, PostDataBuilder)
    pd = builder.build()
    assert pd.item_url == "http://b.com"
    assert pd.category == 2
    assert pd.region == "CA"
    assert pd.source_price == 5.5
    assert pd.source_currency == "CAD"

