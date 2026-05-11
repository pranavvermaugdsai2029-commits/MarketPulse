"""Advanced pricing analysis with statistical trend detection."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import mean, stdev
from typing import Any

from marketpulse.contracts import (
    MarketRecord,
    PricingDelta,
    PricingTrend,
)


@dataclass
class PricingAnalysisConfig:
    """Configuration for pricing analysis."""

    significance_threshold: float = 0.05  # 5% change is significant
    moderate_threshold: float = 0.02  # 2% change is moderate
    min_data_points: int = 2  # Minimum data points for trend analysis
    confidence_level: float = 0.95  # 95% confidence level


class PricingAnalyzer:
    """Advanced pricing analysis with statistical methods."""

    def __init__(self, config: PricingAnalysisConfig | None = None) -> None:
        self.config = config or PricingAnalysisConfig()

    def analyze_weekly_deltas(
        self,
        records: list[MarketRecord],
        weeks_back: int = 4,
    ) -> list[PricingDelta]:
        """Analyze week-over-week pricing changes."""
        if len(records) < self.config.min_data_points:
            return []

        # Group records by competitor and product
        grouped = self._group_by_competitor_product(records)

        deltas = []
        for (competitor, product), record_list in grouped.items():
            # Sort by date
            sorted_records = sorted(record_list, key=lambda r: r.week_start)

            # Analyze weekly changes
            weekly_deltas = self._calculate_weekly_deltas(
                competitor, product, sorted_records, weeks_back
            )
            deltas.extend(weekly_deltas)

        return deltas

    def detect_pricing_trends(
        self,
        records: list[MarketRecord],
        min_weeks: int = 3,
    ) -> list[PricingTrend]:
        """Detect extended pricing trends over time."""
        if len(records) < min_weeks:
            return []

        # Group by competitor and product
        grouped = self._group_by_competitor_product(records)

        trends = []
        for (competitor, product), record_list in grouped.items():
            # Sort by date and analyze trend
            sorted_records = sorted(record_list, key=lambda r: r.week_start)

            if len(sorted_records) >= min_weeks:
                trend = self._calculate_trend(competitor, product, sorted_records)
                trends.append(trend)

        return trends

    def get_significant_changes(
        self,
        deltas: list[PricingDelta],
    ) -> list[PricingDelta]:
        """Filter for statistically significant changes."""
        return [
            delta
            for delta in deltas
            if delta.significance == "significant"
        ]

    def generate_pricing_alerts(
        self,
        deltas: list[PricingDelta],
        trends: list[PricingTrend],
    ) -> list[str]:
        """Generate actionable alerts from pricing analysis."""
        alerts = []

        # Alert on significant price changes
        significant_deltas = self.get_significant_changes(deltas)
        for delta in significant_deltas:
            direction = "increased" if delta.delta_amount > 0 else "decreased"
            alerts.append(
                f"PRICE ALERT: {delta.competitor} {delta.product} price {direction} by "
                f"{abs(delta.delta_percentage):.1f}% (${abs(delta.delta_amount):.2f}) "
                f"from {delta.period_start} to {delta.period_end}"
            )

        # Alert on strong trends
        for trend in trends:
            if trend.trend_strength > 0.7:  # Strong trend
                direction = "upward" if trend.trend_direction == "upward" else "downward"
                alerts.append(
                    f"TREND ALERT: {trend.competitor} {trend.product} showing strong {direction} "
                    f"trend (strength: {trend.trend_strength:.2f}, confidence: {trend.confidence:.2f})"
                )

        return alerts

    def _group_by_competitor_product(
        self,
        records: list[MarketRecord],
    ) -> dict[tuple[str, str], list[MarketRecord]]:
        """Group records by competitor and product."""
        grouped = defaultdict(list)
        for record in records:
            grouped[(record.competitor, record.product)].append(record)
        return dict(grouped)

    def _calculate_weekly_deltas(
        self,
        competitor: str,
        product: str,
        records: list[MarketRecord],
        weeks_back: int,
    ) -> list[PricingDelta]:
        """Calculate week-over-week price changes."""
        deltas = []

        if len(records) < 2:
            return deltas

        # Calculate consecutive week changes
        for i in range(1, min(len(records), weeks_back + 1)):
            current = records[-i]
            previous = records[-i - 1]

            delta_amount = current.price - previous.price
            delta_percentage = (delta_amount / previous.price) * 100 if previous.price > 0 else 0

            # Determine significance
            significance = self._determine_significance(abs(delta_percentage))

            # Determine trend
            trend = self._determine_trend(delta_amount)

            # Calculate confidence based on data consistency
            confidence = self._calculate_confidence(records, i)

            delta = PricingDelta(
                competitor=competitor,
                product=product,
                previous_price=previous.price,
                current_price=current.price,
                delta_amount=delta_amount,
                delta_percentage=delta_percentage,
                significance=significance,
                trend=trend,
                confidence=confidence,
                period_start=previous.week_start,
                period_end=current.week_start,
            )
            deltas.append(delta)

        return deltas

    def _calculate_trend(
        self,
        competitor: str,
        product: str,
        records: list[MarketRecord],
    ) -> PricingTrend:
        """Calculate extended pricing trend."""
        prices = [record.price for record in records]
        dates = [record.week_start for record in records]

        # Calculate basic statistics
        avg_price = mean(prices)
        price_volatility = stdev(prices) if len(prices) > 1 else 0.0

        # Determine trend direction using linear regression
        trend_direction, trend_strength = self._linear_regression_trend(prices)

        # Calculate confidence based on data quality
        confidence = self._calculate_trend_confidence(prices, dates)

        # Identify significant changes within the trend
        significant_changes = []
        weekly_deltas = self._calculate_weekly_deltas(competitor, product, records, len(records))
        for delta in weekly_deltas:
            if delta.significance == "significant":
                significant_changes.append(delta)

        return PricingTrend(
            competitor=competitor,
            product=product,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            confidence=confidence,
            data_points=len(records),
            start_date=dates[0],
            end_date=dates[-1],
            average_price=avg_price,
            price_volatility=price_volatility,
            significant_changes=significant_changes,
        )

    def _determine_significance(self, percentage_change: float) -> str:
        """Determine statistical significance of price change."""
        abs_change = abs(percentage_change)
        if abs_change >= self.config.significance_threshold * 100:
            return "significant"
        elif abs_change >= self.config.moderate_threshold * 100:
            return "moderate"
        else:
            return "minimal"

    def _determine_trend(self, delta_amount: float) -> str:
        """Determine trend direction from price change."""
        if delta_amount > 0:
            return "upward"
        elif delta_amount < 0:
            return "downward"
        else:
            return "stable"

    def _calculate_confidence(
        self,
        records: list[MarketRecord],
        week_index: int,
    ) -> float:
        """Calculate confidence in delta calculation."""
        # Base confidence on data consistency and recency
        base_confidence = 0.8

        # Adjust for recency (more recent = higher confidence)
        recency_factor = 1.0 - (week_index * 0.1)

        # Adjust for data consistency
        if len(records) >= 3:
            prices = [r.price for r in records]
            price_stability = 1.0 - (stdev(prices) / mean(prices)) if mean(prices) > 0 else 0.5
            stability_factor = max(0.5, min(1.0, price_stability))
        else:
            stability_factor = 0.7

        confidence = base_confidence * recency_factor * stability_factor
        return max(0.0, min(1.0, confidence))

    def _linear_regression_trend(self, prices: list[float]) -> tuple[str, float]:
        """Calculate trend using linear regression."""
        if len(prices) < 2:
            return "stable", 0.0

        n = len(prices)
        x = list(range(n))
        y = prices

        # Calculate linear regression
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        sum_y2 = sum(yi * yi for yi in y)

        denominator = (n * sum_x2) - (sum_x * sum_x)
        if denominator == 0:
            return "stable", 0.0

        slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator

        # Determine trend direction
        if slope > 0.01:  # Small threshold to avoid noise
            trend_direction = "upward"
        elif slope < -0.01:
            trend_direction = "downward"
        else:
            trend_direction = "stable"

        # Calculate trend strength based on R-squared
        y_mean = mean(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + (sum_y - slope * sum_x) / n)) ** 2 for xi, yi in zip(x, y))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        trend_strength = math.sqrt(max(0.0, min(1.0, r_squared)))

        return trend_direction, trend_strength

    def _calculate_trend_confidence(
        self,
        prices: list[float],
        dates: list[date],
    ) -> float:
        """Calculate confidence in trend analysis."""
        if len(prices) < 3:
            return 0.5

        # More data points = higher confidence
        data_point_factor = min(1.0, len(prices) / 10.0)

        # Lower volatility = higher confidence
        if mean(prices) > 0:
            volatility = stdev(prices) / mean(prices)
            volatility_factor = max(0.3, 1.0 - min(1.0, volatility))
        else:
            volatility_factor = 0.5

        # Time span consistency
        if len(dates) >= 2:
            time_span = (dates[-1] - dates[0]).days
            time_factor = min(1.0, time_span / 30.0)  # 30 days = full confidence
        else:
            time_factor = 0.5

        confidence = 0.6 * data_point_factor + 0.2 * volatility_factor + 0.2 * time_factor
        return max(0.0, min(1.0, confidence))


def create_pricing_analysis(
    records: list[MarketRecord],
    enable_deltas: bool = True,
    enable_trends: bool = True,
) -> dict[str, Any]:
    """Create comprehensive pricing analysis for integration."""
    analyzer = PricingAnalyzer()

    result = {
        "deltas": [],
        "trends": [],
        "alerts": [],
        "summary": {},
    }

    if enable_deltas:
        deltas = analyzer.analyze_weekly_deltas(records)
        result["deltas"] = [delta.model_dump() for delta in deltas]

    if enable_trends:
        trends = analyzer.detect_pricing_trends(records)
        result["trends"] = [trend.model_dump() for trend in trends]

    # Generate alerts
    deltas_objects = [PricingDelta(**delta) for delta in result["deltas"]]
    trends_objects = [PricingTrend(**trend) for trend in result["trends"]]
    result["alerts"] = analyzer.generate_pricing_alerts(deltas_objects, trends_objects)

    # Create summary
    result["summary"] = {
        "total_deltas": len(result["deltas"]),
        "significant_changes": len([d for d in result["deltas"] if d["significance"] == "significant"]),
        "trends_detected": len(result["trends"]),
        "alerts_generated": len(result["alerts"]),
    }

    return result