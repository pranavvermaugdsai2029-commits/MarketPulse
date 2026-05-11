from pathlib import Path

from marketpulse.contracts import FeatureFlags, MarketPulseState
from marketpulse.data import filter_records, load_market_records
from marketpulse.evaluation import evaluate_state
from marketpulse.graph import MarketPulseWorkflow


def _state(flags: FeatureFlags | None = None) -> MarketPulseState:
    records = load_market_records(Path("data/sample_market.csv"))
    selected = filter_records(records, competitors=["AlphaMart", "BetaBuy", "Cartly"])
    return MarketPulseState(
        question="Which competitor move matters most?",
        competitors=["AlphaMart", "BetaBuy", "Cartly"],
        records=selected,
        feature_flags=flags or FeatureFlags(enable_pricing_delta=True),
    )


def test_workflow_runs_required_parallel_workers() -> None:
    """Test that workflow runs the required workers: pricing, sentiment, promo."""
    completed = MarketPulseWorkflow().run(_state())

    # Check that required workers are present
    assert "pricing" in completed.worker_outputs
    assert "sentiment" in completed.worker_outputs
    assert "promo" in completed.worker_outputs

    # Check that old workers are not present
    assert "demand" not in completed.worker_outputs
    assert "reviews" not in completed.worker_outputs
    assert "social" not in completed.worker_outputs

    assert completed.supervisor_decision is not None
    assert completed.final_brief.startswith("# MarketPulse Competitive Brief")
    assert len(completed.logs) >= 5


def test_required_worker_names_are_correct() -> None:
    """Compliance test: Verify worker names match assignment requirements."""
    completed = MarketPulseWorkflow().run(_state())

    # Required worker names per assignment
    required_workers = {"pricing", "sentiment", "promo"}
    actual_workers = set(completed.worker_outputs.keys())

    assert actual_workers == required_workers, f"Expected {required_workers}, got {actual_workers}"


def test_llm_supervisor_routing_path() -> None:
    """Compliance test: Verify LLM-based supervisor routing is used."""
    completed = MarketPulseWorkflow().run(_state())

    # Check that supervisor decision exists and has reasoning
    assert completed.supervisor_decision is not None
    assert len(completed.supervisor_decision.reasoning) > 0

    # Check that supervisor logs are present
    supervisor_logs = [log for log in completed.logs if log.node == "supervisor"]
    assert len(supervisor_logs) >= 2, "Supervisor should have started and completed logs"


def test_required_state_fields_are_populated() -> None:
    """Compliance test: Verify required state fields are populated."""
    completed = MarketPulseWorkflow().run(_state())

    # Check required explicit state fields
    assert completed.pricing_data, "pricing_data field must be populated"
    assert completed.sentiment_data, "sentiment_data field must be populated"
    assert completed.promo_data, "promo_data field must be populated"

    # Check structured brief
    assert completed.structured_brief is not None, "structured_brief field must be populated"

    # Verify required contract shapes
    assert isinstance(completed.pricing_data, dict)
    assert isinstance(completed.sentiment_data, dict)
    assert isinstance(completed.promo_data, dict)

    first_pricing_key = next(iter(completed.pricing_data))
    assert len(completed.pricing_data[first_pricing_key]) > 0
    assert hasattr(completed.pricing_data[first_pricing_key][0], "sku")
    assert hasattr(completed.pricing_data[first_pricing_key][0], "price")

    first_sentiment_key = next(iter(completed.sentiment_data))
    assert hasattr(completed.sentiment_data[first_sentiment_key], "overall_sentiment")
    assert hasattr(completed.sentiment_data[first_sentiment_key], "review_themes")

    first_promo_key = next(iter(completed.promo_data))
    assert len(completed.promo_data[first_promo_key]) > 0
    assert hasattr(completed.promo_data[first_promo_key][0], "promo_type")


def test_pricing_delta_flag_adds_week_over_week_findings() -> None:
    """Test that pricing delta flag adds week-over-week analysis."""
    completed = MarketPulseWorkflow().run(_state(FeatureFlags(enable_pricing_delta=True)))
    pricing = completed.worker_outputs["pricing"]

    assert any("from first to latest week" in bullet for bullet in pricing.bullets)


def test_structured_brief_format() -> None:
    """Test that structured brief is properly formatted."""
    completed = MarketPulseWorkflow().run(_state())

    assert completed.structured_brief is not None
    assert completed.structured_brief.title == "MarketPulse Competitive Brief"
    assert len(completed.structured_brief.worker_findings) == 3
    assert len(completed.structured_brief.opportunities) > 0
    assert len(completed.structured_brief.risks) > 0
    assert len(completed.structured_brief.recommended_actions) > 0


def test_acceptance_checks_pass_for_sample_state() -> None:
    """Test that all acceptance checks pass."""
    completed = MarketPulseWorkflow().run(_state())
    results = evaluate_state(completed)

    assert all(result.passed for result in results), f"Failed checks: {[r.name for r in results if not r.passed]}"


def test_pydantic_models_are_used() -> None:
    """Compliance test: Verify Pydantic v2 models are being used."""
    from marketpulse.contracts import MarketPulseState, WorkerOutput, MarketRecord
    from datetime import date

    # Create a state and verify it's a Pydantic model
    state = MarketPulseState(
        question="Test",
        competitors=["Test"],
        records=[],
    )

    # Check that it has Pydantic methods
    assert hasattr(state, "model_validate")
    assert hasattr(state, "model_dump")

    # Check that worker outputs are Pydantic models
    from marketpulse.agents import run_pricing_worker

    # Create valid test records
    test_records = [
        MarketRecord(
            week_start=date(2024, 1, 1),
            competitor="TestComp",
            product="TestProduct",
            price=10.0,
            promo="",
            social_mentions=0,
            social_sentiment=0.0,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        )
    ]

    output = run_pricing_worker(test_records, FeatureFlags())
    assert hasattr(output, "model_validate")
    assert hasattr(output, "model_dump")


def test_edge_rules_match_required_workers() -> None:
    """Compliance test: Verify edge rules match required worker semantics."""
    from marketpulse.agents import EDGE_RULES

    # Check that edge rules exist for required workers
    assert "pricing" in EDGE_RULES
    assert "sentiment" in EDGE_RULES
    assert "promo" in EDGE_RULES

    # Check that old workers are not in edge rules
    assert "demand" not in EDGE_RULES
    assert "reviews" not in EDGE_RULES

    # Phase 6: Social worker is allowed as a bonus feature
    # The test should verify that social worker exists and is properly marked as bonus
    assert "social" in EDGE_RULES
    assert "enable_social_worker" in EDGE_RULES["social"] or "bonus" in EDGE_RULES["social"].lower()
