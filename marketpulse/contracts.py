"""Typed contracts shared across data, worker, and graph layers."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

WorkerName = Literal["pricing", "sentiment", "promo", "social"]


class MarketRecord(BaseModel):
    """Normalized market data record with validation."""

    week_start: date
    competitor: str
    product: str
    price: float = Field(gt=0, description="Price must be positive")
    promo: str
    social_mentions: int = Field(ge=0, description="Social mentions must be non-negative")
    social_sentiment: float = Field(ge=-1.0, le=1.0, description="Sentiment between -1 and 1")
    traffic_index: float = Field(ge=0.0, le=100.0, description="Traffic index between 0 and 100")
    review_score: float = Field(ge=0.0, le=5.0, description="Review score between 0 and 5")
    notes: str = Field(default="", description="Additional notes")

    @field_validator("competitor", "product")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("notes")
    @classmethod
    def default_empty_string(cls, v: str) -> str:
        return v if v else ""


class PricePoint(BaseModel):
    """Individual SKU-level pricing data point for a competitor."""

    sku: str
    price: float = Field(gt=0, description="Price must be positive")
    competitor: str
    week_start: date
    product: str


class SentimentSummary(BaseModel):
    """Per-competitor sentiment summary with themes and sample review text."""

    competitor: str
    overall_sentiment: float = Field(ge=-1.0, le=1.0)
    review_themes: list[str] = Field(default_factory=list)
    sample_reviews: list[str] = Field(default_factory=list)
    sentiment_distribution: dict[str, int] = Field(default_factory=dict)
    review_count: int = Field(ge=0, default=0)


class Promotion(BaseModel):
    """Individual promotion artifact per competitor and product."""

    competitor: str
    promo_type: str
    discount_depth: float = Field(ge=0.0, le=1.0)
    promo_copy: str
    start_date: date
    end_date: date | None = None
    product: str | None = None


class FeatureFlags(BaseModel):
    """Feature flags for bonus functionality."""

    enable_social_worker: bool = False
    enable_pricing_delta: bool = False
    enable_weekly_scheduler: bool = False


class NodeLog(BaseModel):
    """Node execution log entry."""

    node: str
    event: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerOutput(BaseModel):
    """Output from a worker agent."""

    worker: WorkerName
    title: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")


class SupervisorDecision(BaseModel):
    """Supervisor routing decision."""

    selected_workers: list[WorkerName]
    skipped_workers: dict[WorkerName, str] = Field(default_factory=dict)
    reasoning: str


class AggregatedInsight(BaseModel):
    """Aggregated insights from all workers."""

    executive_summary: str
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class PricingData(BaseModel):
    """Structured pricing analysis data."""

    lowest_average_price: float
    highest_average_price: float
    price_spread: float
    lowest_priced_competitor: str
    highest_priced_competitor: str
    weekly_deltas: dict[str, float] = Field(default_factory=dict, description="Weekly price changes by competitor")


class SentimentData(BaseModel):
    """Structured sentiment analysis data."""

    overall_sentiment_leader: str
    leader_sentiment_score: float
    sentiment_concern: str
    concern_sentiment_score: float
    sentiment_distribution: dict[str, float] = Field(default_factory=dict, description="Sentiment scores by competitor")


class PromoData(BaseModel):
    """Structured promotion analysis data."""

    most_active_promoter: str
    promotion_frequency: dict[str, int] = Field(default_factory=dict, description="Promo count by competitor")
    promotion_types: dict[str, list[str]] = Field(default_factory=dict, description="Promo types by competitor")
    effectiveness_score: dict[str, float] = Field(default_factory=dict, description="Promo effectiveness by competitor")


class FinalBrief(BaseModel):
    """Structured final brief output."""

    title: str = "MarketPulse Competitive Brief"
    run_id: str
    question: str
    competitors: list[str]
    dispatch_reasoning: str
    executive_summary: str
    worker_findings: list[dict[str, Any]] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    node_logs: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


# Phase 6: Pricing Delta Detection Models

class PricingDelta(BaseModel):
    """Week-over-week pricing change analysis."""

    competitor: str
    product: str
    previous_price: float = Field(gt=0, description="Previous period price")
    current_price: float = Field(gt=0, description="Current period price")
    delta_amount: float = Field(description="Price change amount")
    delta_percentage: float = Field(description="Price change percentage")
    significance: str = Field(description="Statistical significance: significant, moderate, minimal")
    trend: str = Field(description="Price trend direction: upward, downward, stable")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in trend detection")
    period_start: date
    period_end: date


class PricingTrend(BaseModel):
    """Extended pricing trend analysis."""

    competitor: str
    product: str
    trend_direction: str = Field(description="Overall trend: upward, downward, stable")
    trend_strength: float = Field(ge=0.0, le=1.0, description="Trend strength 0-1")
    confidence: float = Field(ge=0.0, le=1.0, description="Statistical confidence")
    data_points: int = Field(ge=0, description="Number of data points analyzed")
    start_date: date
    end_date: date
    average_price: float
    price_volatility: float = Field(ge=0.0, description="Price volatility measure")
    significant_changes: list[PricingDelta] = Field(default_factory=list)


# Phase 6: Social Listening Models

class SocialMention(BaseModel):
    """Individual social media mention."""

    platform: str = Field(description="Social media platform")
    author: str = Field(description="Author username")
    content: str = Field(description="Mention content")
    timestamp: datetime = Field(description="When the mention occurred")
    sentiment: float = Field(ge=-1.0, le=1.0, description="Sentiment score -1 to 1")
    influence_score: float = Field(ge=0.0, le=1.0, description="Influencer score 0-1")
    reach: int = Field(ge=0, description="Estimated reach")
    engagement: int = Field(ge=0, description="Engagement metrics")


class SocialInsight(BaseModel):
    """Aggregated social media intelligence."""

    platform: str
    mention_count: int = Field(ge=0, description="Total mentions")
    sentiment_score: float = Field(ge=-1.0, le=1.0, description="Average sentiment")
    sentiment_trend: str = Field(description="Sentiment trend: improving, declining, stable")
    top_influencers: list[str] = Field(default_factory=list, description="Most influential authors")
    key_topics: list[str] = Field(default_factory=list, description="Trending topics")
    velocity: float = Field(ge=0.0, description="Mentions per hour")
    peak_activity: datetime | None = Field(None, description="Peak activity time")
    engagement_rate: float = Field(ge=0.0, description="Average engagement rate")


class SocialData(BaseModel):
    """Comprehensive social listening data."""

    total_mentions: int = Field(ge=0, description="Total mentions across platforms")
    overall_sentiment: float = Field(ge=-1.0, le=1.0, description="Overall sentiment score")
    sentiment_distribution: dict[str, int] = Field(default_factory=dict, description="Sentiment category counts")
    platform_insights: dict[str, SocialInsight] = Field(default_factory=dict, description="Platform-specific insights")
    top_mentions: list[SocialMention] = Field(default_factory=list, description="Most significant mentions")
    influencer_analysis: dict[str, float] = Field(default_factory=dict, description="Influencer impact scores")
    trend_analysis: str = Field(default="", description="Overall trend analysis")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations")


# Phase 6: Scheduler Models

class ScheduleConfig(BaseModel):
    """Configuration for scheduled executions."""

    enabled: bool = Field(default=False, description="Enable scheduling")
    frequency: str = Field(default="weekly", description="Schedule frequency: weekly, daily, hourly")
    day_of_week: int | None = Field(None, ge=0, le=6, description="Day of week (0-6) for weekly schedules")
    hour: int = Field(default=9, ge=0, le=23, description="Hour of day (0-23)")
    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    max_concurrent: int = Field(default=1, ge=1, description="Maximum concurrent executions")
    timeout_minutes: int = Field(default=30, ge=1, description="Execution timeout in minutes")


class ScheduleExecution(BaseModel):
    """Record of a scheduled execution."""

    execution_id: str = Field(description="Unique execution identifier")
    scheduled_time: datetime = Field(description="When execution was scheduled")
    actual_time: datetime = Field(description="When execution actually started")
    completion_time: datetime | None = Field(None, description="When execution completed")
    status: str = Field(description="Execution status: success, failed, timeout")
    duration_ms: int = Field(ge=0, description="Execution duration in milliseconds")
    error_message: str | None = Field(None, description="Error details if failed")
    competitors: list[str] = Field(default_factory=list, description="Competitors analyzed")
    records_processed: int = Field(ge=0, description="Number of records processed")
    feature_flags: dict[str, bool] = Field(default_factory=dict, description="Feature flags used")


class ScheduleHistory(BaseModel):
    """History of scheduled executions."""

    executions: list[ScheduleExecution] = Field(default_factory=list, description="Execution history")
    total_executions: int = Field(ge=0, default=0, description="Total executions count")
    successful_executions: int = Field(ge=0, default=0, description="Successful executions count")
    failed_executions: int = Field(ge=0, default=0, description="Failed executions count")
    last_execution: datetime | None = Field(None, description="Last execution time")
    next_scheduled: datetime | None = Field(None, description="Next scheduled execution time")

    def add_execution(self, execution: ScheduleExecution) -> None:
        """Add an execution to history."""
        self.executions.append(execution)
        self.total_executions += 1
        if execution.status == "success":
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        self.last_execution = execution.actual_time

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


class MarketPulseState(BaseModel):
    """Complete state for MarketPulse workflow execution."""

    question: str
    competitors: list[str]
    records: list[MarketRecord] = Field(default_factory=list)
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])

    # Workflow state
    supervisor_decision: SupervisorDecision | None = None
    worker_outputs: dict[WorkerName, WorkerOutput] = Field(default_factory=dict)
    aggregated: AggregatedInsight | None = None

    # Required explicit state fields
    pricing_data: dict[str, list[PricePoint]] = Field(default_factory=dict)
    sentiment_data: dict[str, SentimentSummary] = Field(default_factory=dict)
    promo_data: dict[str, list[Promotion]] = Field(default_factory=dict)
    social_data: SocialData | None = None  # Phase 6 bonus field

    # Final outputs
    final_brief: str = ""
    structured_brief: FinalBrief | None = None

    # Logging
    logs: list[NodeLog] = Field(default_factory=list)

    def add_log(self, node: str, event: str, **metadata: Any) -> None:
        """Add a log entry for node execution tracking."""
        self.logs.append(NodeLog(node=node, event=event, metadata=metadata))

    def to_markdown_brief(self) -> str:
        """Convert state to markdown brief format."""
        if self.structured_brief:
            return self._format_structured_brief()
        return self._format_legacy_brief()

    def _format_structured_brief(self) -> str:
        """Format using structured brief data."""
        brief = self.structured_brief
        if not brief:
            return ""

        lines = [
            f"# {brief.title}",
            "",
            f"**Run ID:** `{brief.run_id}`",
            f"**Question:** {brief.question}",
            f"**Competitors:** {', '.join(brief.competitors)}",
            f"**Generated:** {brief.generated_at}",
            "",
            "## Dispatch Reasoning",
            "",
            brief.dispatch_reasoning,
            "",
            "## Executive Summary",
            "",
            brief.executive_summary,
            "",
            "## Worker Findings",
            "",
        ]

        for finding in brief.worker_findings:
            lines.extend([f"### {finding.get('title', 'Unknown')}", "", finding.get("summary", ""), ""])
            lines.extend(f"- {bullet}" for bullet in finding.get("bullets", []))
            lines.append("")

        lines.extend(["## Opportunities", ""])
        lines.extend(f"- {item}" for item in brief.opportunities)
        lines.extend(["", "## Risks", ""])
        lines.extend(f"- {item}" for item in brief.risks)
        lines.extend(["", "## Recommended Actions", ""])
        lines.extend(f"- {item}" for item in brief.recommended_actions)
        lines.extend(["", "## Node I/O Log", ""])
        lines.extend(f"- `{log.get('timestamp', '')}` `{log.get('node', '')}` {log.get('event', '')}" for log in brief.node_logs)

        return "\n".join(lines).strip() + "\n"

    def _format_legacy_brief(self) -> str:
        """Format using legacy state data for backward compatibility."""
        if not self.supervisor_decision or not self.aggregated:
            return ""

        lines = [
            "# MarketPulse Competitive Brief",
            "",
            f"**Run ID:** `{self.run_id}`",
            f"**Question:** {self.question}",
            f"**Competitors:** {', '.join(self.competitors)}",
            "",
            "## Dispatch Reasoning",
            "",
            self.supervisor_decision.reasoning,
            "",
            "## Executive Summary",
            "",
            self.aggregated.executive_summary,
            "",
            "## Worker Findings",
            "",
        ]

        for output in self.worker_outputs.values():
            lines.extend([f"### {output.title}", "", output.summary, ""])
            lines.extend(f"- {bullet}" for bullet in output.bullets)
            lines.append("")

        lines.extend(["## Opportunities", ""])
        lines.extend(f"- {item}" for item in self.aggregated.opportunities)
        lines.extend(["", "## Risks", ""])
        lines.extend(f"- {item}" for item in self.aggregated.risks)
        lines.extend(["", "## Recommended Actions", ""])
        lines.extend(f"- {item}" for item in self.aggregated.recommended_actions)
        lines.extend(["", "## Node I/O Log", ""])
        lines.extend(f"- `{log.timestamp}` `{log.node}` {log.event}" for log in self.logs)

        return "\n".join(lines).strip() + "\n"
