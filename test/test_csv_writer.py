import csv
from modules.models import PostData
from modules.csv_writer import append_post_data_to_csv

def create_sample_post(idx: int) -> PostData:
    return PostData(
        title=f"Title {idx}",
        content=f"Content {idx}",
        image_url="http://img/%d.jpg" % idx,
        category=idx,
        interest="interest",
        warehouse="WH",
        item_url=f"http://example.com/{idx}",
        item_name=f"Item {idx}",
        source_price=idx * 1.0,
        source_currency="USD",
        item_unit_price=idx * 1.0,
        region="US",
    )

def test_append_post_data_to_csv(tmp_path):
    file_path = tmp_path / "out.csv"
    post1 = create_sample_post(1)
    append_post_data_to_csv(str(file_path), post1)
    assert file_path.exists()
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    assert len(reader) == 2  # header + 1 row

    post2 = create_sample_post(2)
    append_post_data_to_csv(str(file_path), post2)
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    assert len(reader) == 3  # header + 2 rows
    assert reader[1][0] == "Title 1"
    assert reader[2][0] == "Title 2"
