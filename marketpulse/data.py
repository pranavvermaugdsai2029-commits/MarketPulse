"""CSV-first data loading and normalization."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from marketpulse.contracts import MarketRecord

REQUIRED_COLUMNS = {
    "week_start",
    "competitor",
    "product",
    "price",
    "promo",
    "social_mentions",
    "social_sentiment",
    "traffic_index",
    "review_score",
    "notes",
}


class DataValidationError(ValueError):
    """Raised when a market data file cannot be normalized safely."""


def load_market_records(path: str | Path) -> list[MarketRecord]:
    """Load and validate market records from CSV file."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Market data file does not exist: {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DataValidationError("CSV file is empty.")
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise DataValidationError(f"CSV is missing required columns: {missing_text}")
        return [_record_from_row(row, line_number=index + 2) for index, row in enumerate(reader)]


def filter_records(
    records: list[MarketRecord],
    competitors: list[str] | None = None,
    product: str | None = None,
) -> list[MarketRecord]:
    """Filter records by competitors and/or product."""
    competitor_set = {item.casefold() for item in competitors or []}
    product_key = product.casefold() if product else None

    return [
        record
        for record in records
        if (not competitor_set or record.competitor.casefold() in competitor_set)
        and (product_key is None or record.product.casefold() == product_key)
    ]


def list_competitors(records: list[MarketRecord]) -> list[str]:
    """Extract unique competitor names from records."""
    return sorted({record.competitor for record in records})


def list_products(records: list[MarketRecord]) -> list[str]:
    """Extract unique product names from records."""
    return sorted({record.product for record in records})


def _record_from_row(row: dict[str, str], line_number: int) -> MarketRecord:
    """Convert CSV row to MarketRecord with validation."""
    try:
        return MarketRecord(
            week_start=date.fromisoformat(_required(row, "week_start", line_number)),
            competitor=_required(row, "competitor", line_number).strip(),
            product=_required(row, "product", line_number).strip(),
            price=_positive_float(row, "price", line_number),
            promo=_required(row, "promo", line_number).strip(),
            social_mentions=_non_negative_int(row, "social_mentions", line_number),
            social_sentiment=_bounded_float(row, "social_sentiment", line_number, -1.0, 1.0),
            traffic_index=_bounded_float(row, "traffic_index", line_number, 0.0, 100.0),
            review_score=_bounded_float(row, "review_score", line_number, 0.0, 5.0),
            notes=_required(row, "notes", line_number).strip(),
        )
    except ValueError as exc:
        raise DataValidationError(f"Invalid row {line_number}: {exc}") from exc


def _required(row: dict[str, str], key: str, line_number: int) -> str:
    """Get required field value."""
    value = row.get(key, "")
    if value is None or value.strip() == "":
        raise ValueError(f"{key} is required")
    return value


def _positive_float(row: dict[str, str], key: str, line_number: int) -> float:
    """Parse and validate positive float field."""
    value = float(_required(row, key, line_number))
    if value <= 0:
        raise ValueError(f"{key} must be greater than zero")
    return value


def _non_negative_int(row: dict[str, str], key: str, line_number: int) -> int:
    """Parse and validate non-negative integer field."""
    value = int(_required(row, key, line_number))
    if value < 0:
        raise ValueError(f"{key} must be non-negative")
    return value


def _bounded_float(
    row: dict[str, str],
    key: str,
    line_number: int,
    lower: float,
    upper: float,
) -> float:
    """Parse and validate bounded float field."""
    value = float(_required(row, key, line_number))
    if value < lower or value > upper:
        raise ValueError(f"{key} must be between {lower} and {upper}")
    return value
