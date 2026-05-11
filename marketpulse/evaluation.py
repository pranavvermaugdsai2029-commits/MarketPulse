"""Evaluation helpers for acceptance-gate checks."""

from __future__ import annotations

from dataclasses import dataclass

from marketpulse.contracts import MarketPulseState


@dataclass(frozen=True)
class EvaluationResult:
    """Result of an evaluation check."""
    name: str
    passed: bool
    detail: str


def evaluate_state(state: MarketPulseState) -> list[EvaluationResult]:
    """Evaluate state against acceptance criteria."""
    return [
        EvaluationResult(
            "parallel_fan_out",
            len(state.worker_outputs) >= 2,
            f"{len(state.worker_outputs)} workers completed.",
        ),
        EvaluationResult(
            "required_workers_present",
            _check_required_workers(state),
            f"Required workers present: {set(state.worker_outputs.keys())}",
        ),
        EvaluationResult(
            "dispatch_reasoning",
            state.supervisor_decision is not None and bool(state.supervisor_decision.reasoning),
            "Supervisor reasoning is present.",
        ),
        EvaluationResult(
            "final_markdown",
            state.final_brief.startswith("# MarketPulse"),
            "Final brief is markdown with expected title.",
        ),
        EvaluationResult(
            "node_logging",
            len(state.logs) >= 5,
            f"{len(state.logs)} node events captured.",
        ),
        EvaluationResult(
            "aggregation",
            state.aggregated is not None and len(state.aggregated.recommended_actions) >= 2,
            "Aggregator produced recommended actions.",
        ),
        EvaluationResult(
            "structured_data_fields",
            _check_structured_data(state),
            "Required structured data fields are populated.",
        ),
        EvaluationResult(
            "structured_brief",
            state.structured_brief is not None,
            "Structured brief is generated.",
        ),
    ]


def _check_required_workers(state: MarketPulseState) -> bool:
    """Check that required workers are present."""
    required = {"pricing", "sentiment", "promo"}
    actual = set(state.worker_outputs.keys())
    return required.issubset(actual)


def _check_structured_data(state: MarketPulseState) -> bool:
    """Check that required structured data fields are populated."""
    return (
        bool(state.pricing_data)
        and bool(state.sentiment_data)
        and bool(state.promo_data)
    )
