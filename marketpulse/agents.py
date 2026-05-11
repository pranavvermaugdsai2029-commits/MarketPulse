"""Worker agents and aggregation logic for MarketPulse."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from marketpulse.contracts import (
    AggregatedInsight,
    FeatureFlags,
    MarketRecord,
    PricePoint,
    Promotion,
    SentimentSummary,
    SupervisorDecision,
    WorkerName,
    WorkerOutput,
)

# Phase 6: Import social listening worker
from marketpulse.social_listening import run_social_worker

BASE_WORKERS: list[WorkerName] = ["pricing", "sentiment", "promo"]
BONUS_WORKERS: list[WorkerName] = ["social"]  # Phase 6 bonus worker

EDGE_RULES: dict[WorkerName, str] = {
    "pricing": "Run when at least one selected competitor has price data.",
    "sentiment": "Run when sentiment data exists for selected competitors.",
    "promo": "Run when promotion data exists for selected competitors.",
    "social": "Run only when enable_social_worker is true (Phase 6 bonus feature).",
}


def route_workers(records: list[MarketRecord], flags: FeatureFlags) -> SupervisorDecision:
    """Route workers using LLM-based supervisor with rule-based fallback."""
    from marketpulse.llm import create_supervisor_router

    import os

    api_key = os.environ.get("GEMINI_API_KEY")
    supervisor = create_supervisor_router(api_key)
    decision = supervisor.route(records, flags)

    # Add social worker if feature flag is enabled (Phase 6 bonus)
    if flags.enable_social_worker and "social" not in decision.selected_workers:
        if records:  # Only add if we have data
            decision.selected_workers.append("social")
            if "social" in decision.skipped_workers:
                del decision.skipped_workers["social"]

    return decision


def run_pricing_worker(records: list[MarketRecord], flags: FeatureFlags) -> WorkerOutput:
    """Analyze pricing data across competitors with optional delta detection."""
    by_competitor = _group_by_competitor(records)
    averages = {name: mean(item.price for item in rows) for name, rows in by_competitor.items()}
    lowest_name = min(averages, key=averages.get)
    highest_name = max(averages, key=averages.get)
    spread = averages[highest_name] - averages[lowest_name]

    bullets = [
        f"{lowest_name} owns the lowest average price at ${averages[lowest_name]:.2f}.",
        f"{highest_name} is highest at ${averages[highest_name]:.2f}, creating a ${spread:.2f} spread.",
    ]

    # Phase 6: Enhanced pricing delta detection
    if flags.enable_pricing_delta:
        from marketpulse.pricing_analysis import PricingAnalyzer

        analyzer = PricingAnalyzer()
        deltas = analyzer.analyze_weekly_deltas(records)
        trends = analyzer.detect_pricing_trends(records)
        alerts = analyzer.generate_pricing_alerts(deltas, trends)

        if deltas:
            bullets.extend(_pricing_delta_bullets(by_competitor))

        if alerts:
            bullets.extend([f"🚨 {alert}" for alert in alerts[:3]])  # Top 3 alerts

    return WorkerOutput(
        worker="pricing",
        title="Pricing intelligence",
        summary=f"Price spread is ${spread:.2f} across selected competitors.",
        bullets=bullets,
        metrics={
            "lowest_average_price": round(averages[lowest_name], 2),
            "highest_average_price": round(averages[highest_name], 2),
            "price_spread": round(spread, 2),
        },
        confidence=0.92,
    )


def run_sentiment_worker(records: list[MarketRecord], flags: FeatureFlags) -> WorkerOutput:
    """Analyze customer sentiment from social mentions and reviews."""
    by_competitor = _group_by_competitor(records)
    sentiment = {
        name: mean(item.social_sentiment for item in rows)
        for name, rows in by_competitor.items()
    }
    leader = max(sentiment, key=sentiment.get)
    concern = min(sentiment, key=sentiment.get)

    # Also analyze review scores if available
    review_scores = {
        name: mean(item.review_score for item in rows)
        for name, rows in by_competitor.items()
    }
    review_leader = max(review_scores, key=review_scores.get)

    bullets = [
        f"{leader} leads sentiment with an average score of {sentiment[leader]:.2f}.",
        f"{concern} has the lowest sentiment at {sentiment[concern]:.2f}.",
        f"{review_leader} has the highest review quality at {review_scores[review_leader]:.2f} out of 5.",
        "Sentiment trends should be monitored alongside pricing changes.",
    ]

    return WorkerOutput(
        worker="sentiment",
        title="Sentiment analysis",
        summary=f"{leader} demonstrates the strongest customer sentiment among competitors.",
        bullets=bullets,
        metrics={
            "sentiment_leader": leader,
            "leader_sentiment_score": round(sentiment[leader], 2),
            "concern_sentiment_score": round(sentiment[concern], 2),
            "review_leader": review_leader,
            "leader_review_score": round(review_scores[review_leader], 2),
        },
        confidence=0.88,
    )


def run_promo_worker(records: list[MarketRecord], flags: FeatureFlags) -> WorkerOutput:
    """Analyze promotion and discount strategies."""
    by_competitor = _group_by_competitor(records)

    # Count promotions by competitor
    promo_counts = {
        name: sum(1 for item in rows if item.promo.strip())
        for name, rows in by_competitor.items()
    }

    # Analyze promotion types
    promo_types: dict[str, list[str]] = {}
    for name, rows in by_competitor.items():
        types = [item.promo.strip() for item in rows if item.promo.strip()]
        promo_types[name] = list(set(types))

    most_active = max(promo_counts, key=promo_counts.get) if promo_counts else "None"
    total_promos = sum(promo_counts.values())

    bullets = [
        f"{most_active} is most promotionally active with {promo_counts[most_active]} promotions.",
        f"Total promotions across competitors: {total_promos}.",
    ]

    # Add promotion type insights
    if promo_types:
        type_count = sum(len(types) for types in promo_types.values())
        bullets.append(f"Competitors are using {type_count} different promotion types.")

        # Add specific promotion types for most active competitor
        if most_active in promo_types and promo_types[most_active]:
            bullets.append(f"{most_active} promotion types: {', '.join(promo_types[most_active][:3])}")

    bullets.append("Promotion frequency should be correlated with traffic and sentiment changes.")

    return WorkerOutput(
        worker="promo",
        title="Promotion analysis",
        summary=f"{most_active} leads in promotional activity with {promo_counts[most_active]} active promotions.",
        bullets=bullets,
        metrics={
            "most_active_promoter": most_active,
            "total_promotions": total_promos,
            "promotion_leader_count": promo_counts.get(most_active, 0),
        },
        confidence=0.85,
    )


def aggregate_outputs(outputs: dict[WorkerName, WorkerOutput]) -> AggregatedInsight:
    """Aggregate worker outputs into consolidated insights."""
    summaries = [output.summary for output in outputs.values()]
    risks = []
    opportunities = []
    actions = []

    if "pricing" in outputs:
        pricing = outputs["pricing"]
        opportunities.append(pricing.bullets[0])
        risks.append("Price gaps can trigger margin pressure if matched without promotion context.")
        actions.append("Set a price-watch threshold for the lowest-priced competitor.")

    if "sentiment" in outputs:
        sentiment = outputs["sentiment"]
        opportunities.append(sentiment.bullets[0])
        risks.append("Negative sentiment trends can amplify the impact of price increases.")
        actions.append("Monitor sentiment trends before and after promotional campaigns.")

    if "promo" in outputs:
        promo = outputs["promo"]
        opportunities.append(promo.bullets[0])
        risks.append("Over-promotion can train customers to wait for discounts.")
        actions.append("Analyze promotion effectiveness alongside traffic and sentiment data.")

    # Phase 6: Social worker insights
    if "social" in outputs:
        social = outputs["social"]
        opportunities.append(social.bullets[0])
        risks.append("Negative social sentiment can spread rapidly and impact brand perception.")
        actions.append("Monitor social conversations and engage with influencers proactively.")

    return AggregatedInsight(
        executive_summary=" ".join(summaries),
        risks=risks,
        opportunities=opportunities,
        recommended_actions=actions,
    )


def run_worker(worker: WorkerName, records: list[MarketRecord], flags: FeatureFlags) -> WorkerOutput:
    """Run a specific worker based on worker name."""
    dispatch = {
        "pricing": run_pricing_worker,
        "sentiment": run_sentiment_worker,
        "promo": run_promo_worker,
        "social": run_social_worker,  # Phase 6 bonus worker
    }
    return dispatch[worker](records, flags)


def _group_by_competitor(records: list[MarketRecord]) -> dict[str, list[MarketRecord]]:
    """Group records by competitor for analysis."""
    grouped: dict[str, list[MarketRecord]] = defaultdict(list)
    for record in records:
        grouped[record.competitor].append(record)
    return dict(grouped)


def _pricing_delta_bullets(
    by_competitor: dict[str, list[MarketRecord]],
) -> list[str]:
    """Generate week-over-week pricing delta bullets."""
    bullets = []
    for competitor, rows in sorted(by_competitor.items()):
        ordered = sorted(rows, key=lambda item: item.week_start)
        if len(ordered) < 2:
            continue
        first = ordered[0].price
        latest = ordered[-1].price
        delta = latest - first
        direction = "increased" if delta > 0 else "decreased" if delta < 0 else "held flat"
        bullets.append(
            f"{competitor} price {direction} by ${abs(delta):.2f} from first to latest week."
        )
    return bullets


def create_pricing_data(
    records: list[MarketRecord],
    outputs: dict[WorkerName, WorkerOutput],
) -> dict[str, list[PricePoint]]:
    """Create required pricing_data shape: dict[str, list[PricePoint]]."""
    if "pricing" not in outputs:
        return {}

    pricing_data: dict[str, list[PricePoint]] = defaultdict(list)
    for record in records:
        sku = f"{record.competitor}_{record.product}".replace(" ", "_")
        pricing_data[record.competitor].append(
            PricePoint(
                sku=sku,
                price=record.price,
                competitor=record.competitor,
                week_start=record.week_start,
                product=record.product,
            )
        )
    return dict(pricing_data)


def create_sentiment_data(
    records: list[MarketRecord],
    outputs: dict[WorkerName, WorkerOutput],
) -> dict[str, SentimentSummary]:
    """Create required sentiment_data shape: dict[str, SentimentSummary]."""
    if "sentiment" not in outputs:
        return {}

    by_competitor = _group_by_competitor(records)
    sentiment_data: dict[str, SentimentSummary] = {}
    for competitor, competitor_records in by_competitor.items():
        sentiment_scores = [row.social_sentiment for row in competitor_records]
        avg_sentiment = mean(sentiment_scores) if sentiment_scores else 0.0

        positive = sum(1 for score in sentiment_scores if score > 0.2)
        negative = sum(1 for score in sentiment_scores if score < -0.2)
        neutral = len(sentiment_scores) - positive - negative

        themes = _derive_sentiment_themes(avg_sentiment)
        sample_reviews = [row.notes for row in competitor_records if row.notes][:3]

        sentiment_data[competitor] = SentimentSummary(
            competitor=competitor,
            overall_sentiment=avg_sentiment,
            review_themes=themes,
            sample_reviews=sample_reviews,
            sentiment_distribution={
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
            },
            review_count=len(competitor_records),
        )
    return sentiment_data


def create_promo_data(
    records: list[MarketRecord],
    outputs: dict[WorkerName, WorkerOutput],
) -> dict[str, list[Promotion]]:
    """Create required promo_data shape: dict[str, list[Promotion]]."""
    if "promo" not in outputs:
        return {}

    promo_data: dict[str, list[Promotion]] = defaultdict(list)
    for record in records:
        promo_copy = record.promo.strip()
        if not promo_copy:
            continue

        promo_data[record.competitor].append(
            Promotion(
                competitor=record.competitor,
                promo_type=_classify_promo_type(promo_copy),
                discount_depth=_infer_discount_depth(promo_copy),
                promo_copy=promo_copy,
                start_date=record.week_start,
                end_date=None,
                product=record.product,
            )
        )
    return dict(promo_data)


def _derive_sentiment_themes(avg_sentiment: float) -> list[str]:
    """Create lightweight themes aligned with overall sentiment direction."""
    if avg_sentiment >= 0.35:
        return ["product quality", "brand trust", "repeat intent"]
    if avg_sentiment >= 0.1:
        return ["value perception", "shipping experience", "fit and comfort"]
    return ["price sensitivity", "service friction", "feature dissatisfaction"]


def _classify_promo_type(promo_copy: str) -> str:
    """Classify promo text into a coarse promotion type."""
    lower = promo_copy.casefold()
    if "free shipping" in lower:
        return "shipping"
    if "bundle" in lower:
        return "bundle"
    if "loyalty" in lower or "points" in lower:
        return "loyalty"
    if "retention" in lower or "trial" in lower or "subscription" in lower:
        return "retention"
    if "code" in lower or "coupon" in lower:
        return "coupon"
    if "sale" in lower or "discount" in lower or "cashback" in lower:
        return "discount"
    return "offer"


def _infer_discount_depth(promo_copy: str) -> float:
    """Infer rough discount depth from promotional copy text."""
    lower = promo_copy.casefold()
    if "flash" in lower:
        return 0.25
    if "weekend sale" in lower:
        return 0.20
    if "coupon" in lower or "code" in lower:
        return 0.15
    if "cashback" in lower:
        return 0.10
    if "free shipping" in lower:
        return 0.08
    if "loyalty" in lower or "points" in lower:
        return 0.10
    return 0.05
