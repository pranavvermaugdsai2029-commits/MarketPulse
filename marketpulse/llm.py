"""LLM adapters with deterministic fallback behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from marketpulse.contracts import (
    FeatureFlags,
    MarketRecord,
    SupervisorDecision,
    WorkerName,
)


class BriefWriter:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


@dataclass
class LocalBriefWriter(BriefWriter):
    """Deterministic writer used for tests and no-key demos."""

    heading: str = "MarketPulse Brief"

    def generate(self, prompt: str) -> str:
        return prompt


class GeminiBriefWriter(BriefWriter):
    def __init__(self, api_key: str, model_name: str) -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. Install requirements.txt or unset GEMINI_API_KEY."
            ) from exc

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str) -> str:
        response = self._model.generate_content(prompt)
        text = getattr(response, "text", "")
        return text.strip() or prompt


def create_brief_writer(api_key: str | None, model_name: str) -> BriefWriter:
    if not api_key:
        return LocalBriefWriter()
    try:
        return GeminiBriefWriter(api_key=api_key, model_name=model_name)
    except RuntimeError:
        return LocalBriefWriter()


class SupervisorRouter:
    """Base class for supervisor routing decisions."""

    def route(self, records: list[MarketRecord], flags: FeatureFlags) -> SupervisorDecision:
        raise NotImplementedError


@dataclass
class RuleBasedSupervisor(SupervisorRouter):
    """Deterministic rule-based supervisor for fallback."""

    def route(self, records: list[MarketRecord], flags: FeatureFlags) -> SupervisorDecision:
        """Route workers based on data availability and feature flags."""
        skipped: dict[WorkerName, str] = {}
        selected: list[WorkerName] = []

        # Check for pricing data availability
        has_pricing = any(record.price > 0 for record in records) if records else False
        if has_pricing:
            selected.append("pricing")
        else:
            skipped["pricing"] = "No pricing data available in records."

        # Check for sentiment data availability
        has_sentiment = any(
            record.social_sentiment != 0 for record in records
        ) if records else False
        if has_sentiment:
            selected.append("sentiment")
        else:
            skipped["sentiment"] = "No sentiment data available in records."

        # Check for promotion data availability
        has_promo = any(record.promo.strip() for record in records) if records else False
        if has_promo:
            selected.append("promo")
        else:
            skipped["promo"] = "No promotion data available in records."

        reasoning = f"Selected {', '.join(selected)} based on available data fields and feature flags."
        if skipped:
            reasoning += f" Skipped {', '.join(skipped.keys())} due to missing data."
        else:
            reasoning += " No workers were skipped."

        return SupervisorDecision(
            selected_workers=selected,
            skipped_workers=skipped,
            reasoning=reasoning,
        )


class LLMSupervisor(SupervisorRouter):
    """LLM-based supervisor with structured output for intelligent routing."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash") -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. Install requirements.txt or unset GEMINI_API_KEY."
            ) from exc

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)
        self._model_name = model_name

    def route(self, records: list[MarketRecord], flags: FeatureFlags) -> SupervisorDecision:
        """Use LLM to make intelligent routing decisions based on data analysis."""
        if not records:
            return SupervisorDecision(
                selected_workers=[],
                skipped_workers={
                    "pricing": "No records available",
                    "sentiment": "No records available",
                    "promo": "No records available",
                },
                reasoning="No records available for analysis.",
            )

        # Analyze data availability
        data_summary = self._analyze_data_availability(records)

        # Build prompt for LLM routing decision
        prompt = self._build_routing_prompt(data_summary, flags)

        try:
            response = self._model.generate_content(prompt)
            decision_text = getattr(response, "text", "")

            # Parse the LLM response into structured decision
            return self._parse_routing_decision(decision_text, records, flags)
        except Exception as exc:
            # Fallback to rule-based on LLM failure
            return RuleBasedSupervisor().route(records, flags)

    def _analyze_data_availability(self, records: list[MarketRecord]) -> dict[str, Any]:
        """Analyze what data is available across records."""
        competitors = list({record.competitor for record in records})
        products = list({record.product for record in records})

        has_pricing = any(record.price > 0 for record in records)
        has_sentiment = any(record.social_sentiment != 0 for record in records)
        has_promo = any(record.promo.strip() for record in records)

        # Calculate some basic statistics
        price_range = (
            (min(record.price for record in records), max(record.price for record in records))
            if has_pricing
            else (0, 0)
        )

        sentiment_range = (
            (
                min(record.social_sentiment for record in records),
                max(record.social_sentiment for record in records),
            )
            if has_sentiment
            else (0, 0)
        )

        promo_count = sum(1 for record in records if record.promo.strip())

        return {
            "competitors": competitors,
            "products": products,
            "record_count": len(records),
            "has_pricing": has_pricing,
            "has_sentiment": has_sentiment,
            "has_promo": has_promo,
            "price_range": price_range,
            "sentiment_range": sentiment_range,
            "promo_count": promo_count,
        }

    def _build_routing_prompt(self, data_summary: dict[str, Any], flags: FeatureFlags) -> str:
        """Build prompt for LLM routing decision."""
        prompt = f"""You are a supervisor for a market intelligence system. Your job is to decide which worker agents to run based on available data.

Available workers:
- pricing: Analyzes pricing data, price spreads, and competitive positioning
- sentiment: Analyzes customer sentiment from social mentions and reviews
- promo: Analyzes promotion and discount strategies

Data Summary:
- Competitors: {', '.join(data_summary['competitors'])}
- Products: {', '.join(data_summary['products'])}
- Total records: {data_summary['record_count']}
- Has pricing data: {data_summary['has_pricing']}
- Has sentiment data: {data_summary['has_sentiment']}
- Has promotion data: {data_summary['has_promo']}

Price range: ${data_summary['price_range'][0]:.2f} - ${data_summary['price_range'][1]:.2f}
Sentiment range: {data_summary['sentiment_range'][0]:.2f} - {data_summary['sentiment_range'][1]:.2f}
Promotion count: {data_summary['promo_count']}

Feature flags:
- Enable social worker: {flags.enable_social_worker}
- Enable pricing delta: {flags.enable_pricing_delta}
- Enable weekly scheduler: {flags.enable_weekly_scheduler}

Your task:
1. Decide which workers to SELECT based on data availability and business value
2. Decide which workers to SKIP and provide a reason
3. Provide clear reasoning for your decisions

Respond in this exact format:
SELECTED: pricing, sentiment, promo
SKIPPED:
- pricing: reason here
- sentiment: reason here
- promo: reason here
REASONING: Your detailed reasoning here (2-3 sentences)

Only select workers that have relevant data available. At least 2 workers should be selected if possible."""

        return prompt

    def _parse_routing_decision(
        self,
        decision_text: str,
        records: list[MarketRecord],
        flags: FeatureFlags,
    ) -> SupervisorDecision:
        """Parse LLM response into structured decision."""
        selected: list[WorkerName] = []
        skipped: dict[WorkerName, str] = {}
        reasoning = "LLM-based routing decision"

        lines = decision_text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("SELECTED:"):
                workers_part = line.replace("SELECTED:", "").strip()
                if workers_part:
                    selected = [
                        worker.strip().lower()
                        for worker in workers_part.split(",")
                        if worker.strip().lower() in ["pricing", "sentiment", "promo"]
                    ]
            elif line.startswith("SKIPPED:"):
                continue
            elif line.startswith("-") and ":" in line:
                parts = line[1:].split(":", 1)
                if len(parts) == 2:
                    worker_name = parts[0].strip().lower()
                    reason = parts[1].strip()
                    if worker_name in ["pricing", "sentiment", "promo"]:
                        skipped[worker_name] = reason
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()

        # Fallback if parsing failed
        if not selected:
            return RuleBasedSupervisor().route(records, flags)

        return SupervisorDecision(
            selected_workers=selected,
            skipped_workers=skipped,
            reasoning=reasoning,
        )


def create_supervisor_router(
    api_key: str | None, model_name: str = "gemini-1.5-flash"
) -> SupervisorRouter:
    """Create appropriate supervisor router based on API key availability."""
    if not api_key:
        return RuleBasedSupervisor()
    try:
        return LLMSupervisor(api_key=api_key, model_name=model_name)
    except RuntimeError:
        return RuleBasedSupervisor()
