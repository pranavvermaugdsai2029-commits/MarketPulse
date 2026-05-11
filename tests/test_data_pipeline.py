from pathlib import Path

import pytest

from marketpulse.data import DataValidationError, filter_records, list_competitors, load_market_records


def test_load_market_records_from_sample() -> None:
    records = load_market_records(Path("data/sample_market.csv"))

    assert len(records) == 12
    assert list_competitors(records) == ["AlphaMart", "BetaBuy", "Cartly", "DirectCo"]
    assert records[0].price == 49.99


def test_filter_records_by_competitor_and_product() -> None:
    records = load_market_records(Path("data/sample_market.csv"))
    filtered = filter_records(records, competitors=["Cartly"], product="Essentials Box")

    assert len(filtered) == 3
    assert {record.competitor for record in filtered} == {"Cartly"}


def test_invalid_csv_reports_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("competitor,price\nAlphaMart,1.0\n", encoding="utf-8")

    with pytest.raises(DataValidationError, match="missing required columns"):
        load_market_records(path)
