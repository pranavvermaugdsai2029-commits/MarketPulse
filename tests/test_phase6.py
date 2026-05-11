"""Comprehensive tests for Phase 6 bonus features."""

from pathlib import Path
from datetime import date, datetime

from marketpulse.contracts import (
    FeatureFlags,
    MarketPulseState,
    ScheduleConfig,
    PricingDelta,
    PricingTrend,
    SocialData,
)
from marketpulse.data import filter_records, load_market_records
from marketpulse.evaluation import evaluate_state
from marketpulse.graph import MarketPulseWorkflow
from marketpulse.pricing_analysis import (
    PricingAnalyzer,
    PricingAnalysisConfig,
    create_pricing_analysis,
)
from marketpulse.social_listening import (
    SocialSentimentAnalyzer,
    SocialMentionProcessor,
    SocialInsightGenerator,
    run_social_worker,
    create_social_data,
)
from marketpulse.scheduler import (
    SchedulerEngine,
    ScheduleManager,
    create_schedule_manager,
)


def _state(flags: FeatureFlags | None = None) -> MarketPulseState:
    """Create test state with sample data."""
    records = load_market_records(Path("data/sample_market.csv"))
    selected = filter_records(records, competitors=["AlphaMart", "BetaBuy", "Cartly"])
    return MarketPulseState(
        question="Which competitor move matters most?",
        competitors=["AlphaMart", "BetaBuy", "Cartly"],
        records=selected,
        feature_flags=flags or FeatureFlags(
            enable_social_worker=True,
            enable_pricing_delta=True,
            enable_weekly_scheduler=True,
        ),
    )


# Phase 6: Pricing Delta Detection Tests

def test_pricing_analyzer_initializes() -> None:
    """Test that pricing analyzer initializes correctly."""
    config = PricingAnalysisConfig()
    analyzer = PricingAnalyzer(config)

    assert analyzer.config == config
    assert analyzer.config.significance_threshold == 0.05
    assert analyzer.config.min_data_points == 2


def test_pricing_analyzer_weekly_deltas() -> None:
    """Test weekly delta calculation."""
    from marketpulse.contracts import MarketRecord

    records = [
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
        ),
        MarketRecord(
            week_start=date(2024, 1, 8),
            competitor="TestComp",
            product="TestProduct",
            price=12.0,
            promo="",
            social_mentions=0,
            social_sentiment=0.0,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
    ]

    analyzer = PricingAnalyzer()
    deltas = analyzer.analyze_weekly_deltas(records)

    assert len(deltas) == 1
    assert deltas[0].competitor == "TestComp"
    assert deltas[0].product == "TestProduct"
    assert deltas[0].previous_price == 10.0
    assert deltas[0].current_price == 12.0
    assert deltas[0].delta_amount == 2.0
    assert deltas[0].delta_percentage == 20.0


def test_pricing_analyzer_trend_detection() -> None:
    """Test pricing trend detection."""
    from marketpulse.contracts import MarketRecord

    records = [
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
        ),
        MarketRecord(
            week_start=date(2024, 1, 8),
            competitor="TestComp",
            product="TestProduct",
            price=11.0,
            promo="",
            social_mentions=0,
            social_sentiment=0.0,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
        MarketRecord(
            week_start=date(2024, 1, 15),
            competitor="TestComp",
            product="TestProduct",
            price=12.0,
            promo="",
            social_mentions=0,
            social_sentiment=0.0,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
    ]

    analyzer = PricingAnalyzer()
    trends = analyzer.detect_pricing_trends(records)

    assert len(trends) == 1
    assert trends[0].competitor == "TestComp"
    assert trends[0].trend_direction == "upward"
    assert trends[0].trend_strength > 0.5  # Should be strong upward trend


def test_pricing_analyzer_significance_detection() -> None:
    """Test statistical significance detection."""
    from marketpulse.contracts import MarketRecord

    # Create records with significant price change
    records = [
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
        ),
        MarketRecord(
            week_start=date(2024, 1, 8),
            competitor="TestComp",
            product="TestProduct",
            price=11.0,  # 10% increase - should be significant
            promo="",
            social_mentions=0,
            social_sentiment=0.0,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
    ]

    analyzer = PricingAnalyzer()
    deltas = analyzer.analyze_weekly_deltas(records)

    assert len(deltas) == 1
    assert deltas[0].significance == "significant"


def test_pricing_analyzer_alert_generation() -> None:
    """Test pricing alert generation."""
    from marketpulse.contracts import MarketRecord

    records = [
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
        ),
        MarketRecord(
            week_start=date(2024, 1, 8),
            competitor="TestComp",
            product="TestProduct",
            price=12.0,
            promo="",
            social_mentions=0,
            social_sentiment=0.0,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
    ]

    analyzer = PricingAnalyzer()
    deltas = analyzer.analyze_weekly_deltas(records)
    trends = analyzer.detect_pricing_trends(records)
    alerts = analyzer.generate_pricing_alerts(deltas, trends)

    assert len(alerts) > 0
    assert any("PRICE ALERT" in alert for alert in alerts)


def test_create_pricing_analysis_integration() -> None:
    """Test comprehensive pricing analysis creation."""
    records = load_market_records(Path("data/sample_market.csv"))

    analysis = create_pricing_analysis(
        records,
        enable_deltas=True,
        enable_trends=True,
    )

    assert "deltas" in analysis
    assert "trends" in analysis
    assert "alerts" in analysis
    assert "summary" in analysis

    assert len(analysis["deltas"]) > 0
    assert analysis["summary"]["total_deltas"] > 0


# Phase 6: Social Listening Tests

def test_social_sentiment_analyzer() -> None:
    """Test sentiment analysis functionality."""
    analyzer = SocialSentimentAnalyzer()

    # Test positive sentiment
    positive_score = analyzer.analyze_sentiment("This is a great and amazing product!")
    assert positive_score > 0.5

    # Test negative sentiment
    negative_score = analyzer.analyze_sentiment("This is terrible and awful, I hate it!")
    assert negative_score < -0.5

    # Test neutral sentiment
    neutral_score = analyzer.analyze_sentiment("This product is okay.")
    assert -0.3 < neutral_score < 0.3


def test_social_sentiment_batch_analysis() -> None:
    """Test batch sentiment analysis."""
    analyzer = SocialSentimentAnalyzer()

    texts = [
        "Great product!",
        "Terrible experience",
        "It's okay",
        "Amazing service",
        "Disappointing quality",
    ]

    scores = analyzer.batch_analyze(texts)

    assert len(scores) == len(texts)
    assert all(-1.0 <= score <= 1.0 for score in scores)


def test_social_mention_processor() -> None:
    """Test social mention processing."""
    from marketpulse.contracts import MarketRecord

    records = [
        MarketRecord(
            week_start=date(2024, 1, 1),
            competitor="TestComp",
            product="TestProduct",
            price=10.0,
            promo="",
            social_mentions=5,
            social_sentiment=0.5,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
    ]

    processor = SocialMentionProcessor()
    mentions = processor.create_mentions_from_records(records)

    assert len(mentions) > 0
    assert all(mention.platform for mention in mentions)
    assert all(mention.author for mention in mentions)


def test_social_influencer_analysis() -> None:
    """Test influencer analysis."""
    from marketpulse.social_listening import SocialMention

    mentions = [
        SocialMention(
            platform="twitter",
            author="user1",
            content="Great product!",
            timestamp=datetime.now(),
            sentiment=0.8,
            influence_score=0.9,
            reach=10000,
            engagement=500
        ),
        SocialMention(
            platform="twitter",
            author="user2",
            content="Okay product",
            timestamp=datetime.now(),
            sentiment=0.2,
            influence_score=0.3,
            reach=1000,
            engagement=50
        ),
    ]

    processor = SocialMentionProcessor()
    influencers = processor.analyze_influencers(mentions)

    assert len(influencers) > 0
    assert "user1" in influencers  # Higher influence should be ranked first


def test_social_topic_extraction() -> None:
    """Test key topic extraction."""
    from marketpulse.social_listening import SocialMention

    mentions = [
        SocialMention(
            platform="twitter",
            author="user1",
            content="Great product quality and amazing service!",
            timestamp=datetime.now(),
            sentiment=0.8,
            influence_score=0.9,
            reach=10000,
            engagement=500
        ),
        SocialMention(
            platform="twitter",
            author="user2",
            content="Product quality is good but service is slow",
            timestamp=datetime.now(),
            sentiment=0.2,
            influence_score=0.3,
            reach=1000,
            engagement=50
        ),
    ]

    processor = SocialMentionProcessor()
    topics = processor.extract_key_topics(mentions)

    assert len(topics) > 0
    assert any("quality" in topic.lower() for topic in topics)


def test_social_insight_generation() -> None:
    """Test social insight generation."""
    from marketpulse.social_listening import SocialMention

    mentions = [
        SocialMention(
            platform="twitter",
            author="user1",
            content="Great product!",
            timestamp=datetime.now(),
            sentiment=0.8,
            influence_score=0.9,
            reach=10000,
            engagement=500
        ),
        SocialMention(
            platform="facebook",
            author="user2",
            content="Amazing service!",
            timestamp=datetime.now(),
            sentiment=0.7,
            influence_score=0.8,
            reach=5000,
            engagement=300
        ),
    ]

    generator = SocialInsightGenerator()
    insights = generator.generate_platform_insights(mentions)

    assert "twitter" in insights
    assert "facebook" in insights
    assert insights["twitter"].mention_count > 0
    assert insights["facebook"].mention_count > 0


def test_run_social_worker() -> None:
    """Test social worker execution."""
    from marketpulse.contracts import MarketRecord

    records = [
        MarketRecord(
            week_start=date(2024, 1, 1),
            competitor="TestComp",
            product="TestProduct",
            price=10.0,
            promo="",
            social_mentions=10,
            social_sentiment=0.5,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
    ]

    flags = FeatureFlags(enable_social_worker=True)
    output = run_social_worker(records, flags)

    assert output.worker == "social"
    assert output.title == "Social listening"
    assert len(output.bullets) > 0
    assert "total_mentions" in output.metrics
    assert output.metrics["total_mentions"] > 0


def test_create_social_data() -> None:
    """Test social data creation."""
    from marketpulse.agents import run_social_worker
    from marketpulse.contracts import MarketRecord

    records = [
        MarketRecord(
            week_start=date(2024, 1, 1),
            competitor="TestComp",
            product="TestProduct",
            price=10.0,
            promo="",
            social_mentions=10,
            social_sentiment=0.5,
            traffic_index=50.0,
            review_score=4.0,
            notes=""
        ),
    ]

    flags = FeatureFlags(enable_social_worker=True)
    worker_output = run_social_worker(records, flags)
    social_data = create_social_data(worker_output)

    assert social_data.total_mentions > 0
    assert social_data.overall_sentiment >= -1.0
    assert social_data.overall_sentiment <= 1.0


# Phase 6: Scheduler Tests

def test_schedule_config_validation() -> None:
    """Test schedule configuration validation."""
    # Valid config
    config = ScheduleConfig(
        enabled=True,
        frequency="weekly",
        day_of_week=1,  # Monday
        hour=9,
        timezone="UTC",
    )

    assert config.enabled == True
    assert config.frequency == "weekly"
    assert config.day_of_week == 1
    assert config.hour == 9


def test_schedule_manager_creation() -> None:
    """Test schedule manager creation."""
    workflow = MarketPulseWorkflow()
    manager = create_schedule_manager(workflow)

    assert manager is not None
    assert manager.workflow == workflow
    assert manager.config.enabled == False  # Default is disabled


def test_schedule_manager_configuration() -> None:
    """Test schedule manager configuration."""
    workflow = MarketPulseWorkflow()
    manager = create_schedule_manager(workflow)

    config = ScheduleConfig(
        enabled=True,
        frequency="daily",
        hour=10,
        timezone="UTC",
    )

    manager.configure_schedule(config)

    assert manager.config.enabled == True
    assert manager.config.frequency == "daily"
    assert manager.config.hour == 10


def test_schedule_manager_status() -> None:
    """Test schedule manager status reporting."""
    workflow = MarketPulseWorkflow()
    manager = create_schedule_manager(workflow)

    status = manager.get_status()

    assert "enabled" in status
    assert "running" in status
    assert "config" in status
    assert status["enabled"] == False
    assert status["running"] == False


def test_scheduler_engine_initialization() -> None:
    """Test scheduler engine initialization."""
    workflow = MarketPulseWorkflow()
    config = ScheduleConfig(enabled=True, frequency="daily", hour=9)

    engine = SchedulerEngine(config, workflow)

    assert engine.config == config
    assert engine.workflow == workflow
    assert engine.state.is_running == False


def test_scheduler_immediate_execution() -> None:
    """Test immediate workflow execution."""
    workflow = MarketPulseWorkflow()
    config = ScheduleConfig(enabled=True, frequency="daily", hour=9)

    engine = SchedulerEngine(config, workflow)
    execution = engine.execute_now()

    assert execution.execution_id.startswith("exec_")
    assert execution.status in ["success", "failed"]
    assert execution.scheduled_time is not None
    assert execution.actual_time is not None


# Phase 6: Integration Tests

def test_phase6_integration_with_all_features() -> None:
    """Test complete Phase 6 integration."""
    flags = FeatureFlags(
        enable_social_worker=True,
        enable_pricing_delta=True,
        enable_weekly_scheduler=True,
    )

    completed = MarketPulseWorkflow().run(_state(flags))

    # Verify all workers including social
    assert "pricing" in completed.worker_outputs
    assert "sentiment" in completed.worker_outputs
    assert "promo" in completed.worker_outputs
    assert "social" in completed.worker_outputs

    # Verify enhanced pricing worker
    pricing_output = completed.worker_outputs["pricing"]
    assert len(pricing_output.bullets) > 2  # Should have delta analysis

    # Verify social worker output
    social_output = completed.worker_outputs["social"]
    assert social_output.metrics["total_mentions"] > 0

    # Verify structured data
    assert completed.pricing_data is not None
    assert completed.sentiment_data is not None
    assert completed.promo_data is not None
    assert completed.social_data is not None

    # Verify final brief includes all workers
    assert "Social listening" in completed.final_brief


def test_phase6_feature_flags_work_correctly() -> None:
    """Test that Phase 6 feature flags control behavior correctly."""
    # Test with all features disabled
    flags_disabled = FeatureFlags(
        enable_social_worker=False,
        enable_pricing_delta=False,
        enable_weekly_scheduler=False,
    )

    completed_disabled = MarketPulseWorkflow().run(_state(flags_disabled))

    # Social worker should not be present
    assert "social" not in completed_disabled.worker_outputs

    # Test with all features enabled
    flags_enabled = FeatureFlags(
        enable_social_worker=True,
        enable_pricing_delta=True,
        enable_weekly_scheduler=True,
    )

    completed_enabled = MarketPulseWorkflow().run(_state(flags_enabled))

    # Social worker should be present
    assert "social" in completed_enabled.worker_outputs

    # Pricing should have enhanced analysis
    pricing_enabled = completed_enabled.worker_outputs["pricing"]
    pricing_disabled = completed_disabled.worker_outputs["pricing"]

    # Enhanced version should have more bullets (delta analysis)
    assert len(pricing_enabled.bullets) >= len(pricing_disabled.bullets)


def test_phase6_backward_compatibility() -> None:
    """Test that Phase 6 features don't break existing functionality."""
    # Run with all Phase 6 features explicitly disabled for backward compatibility test
    completed = MarketPulseWorkflow().run(_state(FeatureFlags(
        enable_social_worker=False,
        enable_pricing_delta=False,
        enable_weekly_scheduler=False,
    )))

    # Core functionality should still work
    assert len(completed.worker_outputs) >= 2  # At least 2 workers
    assert completed.supervisor_decision is not None
    assert completed.aggregated is not None
    assert completed.final_brief.startswith("# MarketPulse")

    # Evaluation should pass
    results = evaluate_state(completed)

    # Debug: print which checks are failing
    failed_checks = [r for r in results if not r.passed]
    if failed_checks:
        print(f"Failed evaluation checks: {[f.name for f in failed_checks]}")
        for check in failed_checks:
            print(f"  {check.name}: {check.detail}")

    assert all(result.passed for result in results), f"Failed checks: {[r.name for r in results if not r.passed]}"


def test_phase6_performance_acceptable() -> None:
    """Test that Phase 6 features don't significantly impact performance."""
    import time

    # Measure time without Phase 6 features
    start = time.time()
    completed_basic = MarketPulseWorkflow().run(_state(FeatureFlags()))
    basic_time = time.time() - start

    # Measure time with Phase 6 features
    start = time.time()
    completed_enhanced = MarketPulseWorkflow().run(_state(
        FeatureFlags(
            enable_social_worker=True,
            enable_pricing_delta=True,
            enable_weekly_scheduler=True,
        )
    ))
    enhanced_time = time.time() - start

    # Enhanced version should not be more than 3x slower
    assert enhanced_time < basic_time * 3

    # Both should complete in reasonable time
    assert basic_time < 10.0  # 10 seconds max
    assert enhanced_time < 30.0  # 30 seconds max


def test_phase6_error_handling() -> None:
    """Test that Phase 6 features handle errors gracefully."""
    # Test with empty records
    empty_state = MarketPulseState(
        question="Test",
        competitors=["Test"],
        records=[],
        feature_flags=FeatureFlags(
            enable_social_worker=True,
            enable_pricing_delta=True,
        ),
    )

    # Should not crash, but handle gracefully
    try:
        completed = MarketPulseWorkflow().run(empty_state)
        # Should complete without crashing
        assert True
    except Exception as e:
        # If it does crash, it should be a meaningful error
        assert "At least two workers" in str(e) or "No records" in str(e)


def test_phase6_data_validation() -> None:
    """Test that Phase 6 features validate data properly."""
    # Test pricing analysis with invalid data
    from marketpulse.pricing_analysis import PricingAnalyzer

    analyzer = PricingAnalyzer()

    # Empty records should return empty results
    empty_deltas = analyzer.analyze_weekly_deltas([])
    assert len(empty_deltas) == 0

    empty_trends = analyzer.detect_pricing_trends([])
    assert len(empty_trends) == 0

    # Test social analysis with invalid data
    from marketpulse.social_listening import SocialSentimentAnalyzer

    sentiment_analyzer = SocialSentimentAnalyzer()

    # Empty text should return neutral sentiment
    empty_sentiment = sentiment_analyzer.analyze_sentiment("")
    assert empty_sentiment == 0.0

    # None text should handle gracefully
    none_sentiment = sentiment_analyzer.analyze_sentiment(None)  # type: ignore
    assert none_sentiment == 0.0