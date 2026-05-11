"""Advanced social listening worker with sentiment analysis."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from marketpulse.contracts import (
    MarketRecord,
    SocialData,
    SocialInsight,
    SocialMention,
    WorkerOutput,
)


@dataclass
class SocialAnalysisConfig:
    """Configuration for social listening analysis."""

    min_mentions_for_trend: int = 5
    sentiment_threshold: float = 0.3
    influence_threshold: float = 0.6
    velocity_window_hours: int = 24
    top_influencers_count: int = 5
    key_topics_count: int = 5


class SocialSentimentAnalyzer:
    """Advanced sentiment analysis for social media."""

    def __init__(self, config: SocialAnalysisConfig | None = None) -> None:
        self.config = config or SocialAnalysisConfig()
        self._positive_words = {
            "great", "awesome", "excellent", "amazing", "love", "best",
            "fantastic", "wonderful", "outstanding", "perfect", "happy",
            "good", "nice", "brilliant", "superb", "exceptional"
        }
        self._negative_words = {
            "bad", "terrible", "awful", "worst", "hate", "horrible",
            "disappointing", "poor", "sad", "angry", "frustrated",
            "annoying", "useless", "waste", "boring", "dreadful"
        }

    def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text using keyword analysis."""
        if not text:
            return 0.0

        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        positive_count = sum(1 for word in words if word in self._positive_words)
        negative_count = sum(1 for word in words if word in self._negative_words)

        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            return 0.0

        # Calculate sentiment score between -1 and 1
        sentiment = (positive_count - negative_count) / total_sentiment_words
        return max(-1.0, min(1.0, sentiment))

    def batch_analyze(self, texts: list[str]) -> list[float]:
        """Analyze sentiment for multiple texts."""
        return [self.analyze_sentiment(text) for text in texts]


class SocialMentionProcessor:
    """Process and analyze social media mentions."""

    def __init__(self, config: SocialAnalysisConfig | None = None) -> None:
        self.config = config or SocialAnalysisConfig()
        self.sentiment_analyzer = SocialSentimentAnalyzer(config)

    def create_mentions_from_records(
        self,
        records: list[MarketRecord],
    ) -> list[SocialMention]:
        """Create social mentions from market records."""
        mentions = []

        for record in records:
            # Simulate social mentions from record data
            mention_count = max(1, record.social_mentions)

            # Create simulated mentions based on data
            for i in range(min(mention_count, 10)):  # Limit to prevent explosion
                mention = self._create_simulated_mention(record, i)
                mentions.append(mention)

        return mentions

    def _create_simulated_mention(
        self,
        record: MarketRecord,
        index: int,
    ) -> SocialMention:
        """Create a simulated social mention from market record."""
        # Generate realistic social media content
        platforms = ["twitter", "facebook", "instagram", "linkedin", "tiktok"]
        platform = platforms[index % len(platforms)]

        # Generate content based on sentiment
        sentiment = record.social_sentiment
        if sentiment > 0.3:
            content = f"Just tried {record.competitor}'s {record.product} - really impressed with the quality!"
        elif sentiment < -0.3:
            content = f"Disappointed with {record.competitor}'s {record.product} - not worth the price."
        else:
            content = f"Checked out {record.competitor}'s {record.product} - it's okay, nothing special."

        # Calculate influence based on various factors
        influence_score = min(1.0, (record.review_score / 5.0) * 0.8 + (record.traffic_index / 100.0) * 0.2)

        # Estimate reach based on influence
        reach = int(influence_score * 10000) + (record.social_mentions * 100)

        # Calculate engagement
        engagement = int(reach * 0.05)  # 5% engagement rate

        # Vary timestamp slightly
        base_time = datetime.now()
        time_offset = timedelta(hours=index)
        timestamp = base_time - time_offset

        return SocialMention(
            platform=platform,
            author=f"user_{index}_{record.competitor.lower()}",
            content=content,
            timestamp=timestamp,
            sentiment=sentiment,
            influence_score=influence_score,
            reach=reach,
            engagement=engagement,
        )

    def analyze_influencers(
        self,
        mentions: list[SocialMention],
    ) -> dict[str, float]:
        """Analyze and rank influencers."""
        influencer_scores = defaultdict(float)

        for mention in mentions:
            # Score based on influence, engagement, and sentiment quality
            score = (
                mention.influence_score * 0.4 +
                (mention.engagement / max(1, mention.reach)) * 0.3 +
                (abs(mention.sentiment) * 0.3)
            )
            influencer_scores[mention.author] += score

        # Normalize scores
        if influencer_scores:
            max_score = max(influencer_scores.values())
            influencer_scores = {
                author: score / max_score
                for author, score in influencer_scores.items()
            }

        return dict(sorted(influencer_scores.items(), key=lambda x: x[1], reverse=True))

    def extract_key_topics(
        self,
        mentions: list[SocialMention],
    ) -> list[str]:
        """Extract key topics from mentions."""
        all_words = []
        for mention in mentions:
            words = re.findall(r'\b\w+\b', mention.content.lower())
            all_words.extend(words)

        # Filter out common words and get most frequent
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "over", "after"
        }

        filtered_words = [word for word in all_words if word not in stop_words and len(word) > 3]
        word_counts = Counter(filtered_words)

        return [word for word, count in word_counts.most_common(self.config.key_topics_count)]


class SocialInsightGenerator:
    """Generate comprehensive social insights."""

    def __init__(self, config: SocialAnalysisConfig | None = None) -> None:
        self.config = config or SocialAnalysisConfig()
        self.processor = SocialMentionProcessor(config)

    def generate_platform_insights(
        self,
        mentions: list[SocialMention],
    ) -> dict[str, SocialInsight]:
        """Generate insights for each platform."""
        # Group by platform
        platform_mentions = defaultdict(list)
        for mention in mentions:
            platform_mentions[mention.platform].append(mention)

        insights = {}
        for platform, platform_mention_list in platform_mentions.items():
            insight = self._create_platform_insight(platform, platform_mention_list)
            insights[platform] = insight

        return insights

    def _create_platform_insight(
        self,
        platform: str,
        mentions: list[SocialMention],
    ) -> SocialInsight:
        """Create insight for a specific platform."""
        if not mentions:
            return SocialInsight(
                platform=platform,
                mention_count=0,
                sentiment_score=0.0,
                sentiment_trend="stable",
                top_influencers=[],
                key_topics=[],
                velocity=0.0,
            )

        # Calculate basic metrics
        mention_count = len(mentions)
        sentiment_scores = [m.sentiment for m in mentions]
        avg_sentiment = mean(sentiment_scores)

        # Determine sentiment trend
        sentiment_trend = self._determine_sentiment_trend(sentiment_scores)

        # Get top influencers
        influencer_analysis = self.processor.analyze_influencers(mentions)
        top_influencers = list(influencer_analysis.keys())[:self.config.top_influencers_count]

        # Extract key topics
        key_topics = self.processor.extract_key_topics(mentions)

        # Calculate velocity (mentions per hour)
        if len(mentions) >= 2:
            time_span = (mentions[0].timestamp - mentions[-1].timestamp).total_seconds()
            velocity = (len(mentions) / max(1, time_span)) * 3600 if time_span > 0 else 0.0
        else:
            velocity = 0.0

        # Find peak activity
        peak_activity = max(mentions, key=lambda m: m.reach).timestamp if mentions else None

        # Calculate engagement rate
        total_reach = sum(m.reach for m in mentions)
        total_engagement = sum(m.engagement for m in mentions)
        engagement_rate = (total_engagement / total_reach) if total_reach > 0 else 0.0

        return SocialInsight(
            platform=platform,
            mention_count=mention_count,
            sentiment_score=avg_sentiment,
            sentiment_trend=sentiment_trend,
            top_influencers=top_influencers,
            key_topics=key_topics,
            velocity=velocity,
            peak_activity=peak_activity,
            engagement_rate=engagement_rate,
        )

    def _determine_sentiment_trend(self, sentiment_scores: list[float]) -> str:
        """Determine sentiment trend direction."""
        if len(sentiment_scores) < 3:
            return "stable"

        # Compare first third with last third
        split_point = len(sentiment_scores) // 3
        early_sentiment = mean(sentiment_scores[:split_point])
        late_sentiment = mean(sentiment_scores[-split_point:])

        difference = late_sentiment - early_sentiment

        if difference > 0.1:
            return "improving"
        elif difference < -0.1:
            return "declining"
        else:
            return "stable"


def run_social_worker(
    records: list[MarketRecord],
    flags: Any,  # FeatureFlags
) -> WorkerOutput:
    """Run the social listening worker with advanced analysis."""
    config = SocialAnalysisConfig()
    processor = SocialMentionProcessor(config)
    insight_generator = SocialInsightGenerator(config)

    # Create social mentions from records
    mentions = processor.create_mentions_from_records(records)

    if not mentions:
        return WorkerOutput(
            worker="social",
            title="Social listening",
            summary="No social mentions available for analysis.",
            bullets=["No social data found in the provided records."],
            metrics={"mention_count": 0},
            confidence=0.0,
        )

    # Generate platform insights
    platform_insights = insight_generator.generate_platform_insights(mentions)

    # Analyze influencers
    influencer_analysis = processor.analyze_influencers(mentions)

    # Extract key topics
    key_topics = processor.extract_key_topics(mentions)

    # Calculate overall metrics
    total_mentions = len(mentions)
    sentiment_scores = [m.sentiment for m in mentions]
    overall_sentiment = mean(sentiment_scores)

    # Determine sentiment distribution
    positive_count = sum(1 for s in sentiment_scores if s > 0.3)
    negative_count = sum(1 for s in sentiment_scores if s < -0.3)
    neutral_count = total_mentions - positive_count - negative_count

    sentiment_distribution = {
        "positive": positive_count,
        "negative": negative_count,
        "neutral": neutral_count,
    }

    # Generate trend analysis
    top_platform = max(platform_insights.keys(), key=lambda p: platform_insights[p].mention_count)
    top_insight = platform_insights[top_platform]

    trend_analysis = (
        f"Social conversation is {top_insight.sentiment_trend} with {total_mentions} total mentions. "
        f"Top platform is {top_platform} with {top_insight.mention_count} mentions. "
        f"Overall sentiment is {overall_sentiment:.2f}."
    )

    # Generate recommendations
    recommendations = []
    if overall_sentiment > 0.3:
        recommendations.append("Leverage positive sentiment in marketing campaigns.")
    elif overall_sentiment < -0.3:
        recommendations.append("Address negative sentiment through customer service improvements.")

    if influencer_analysis:
        top_influencer = list(influencer_analysis.keys())[0]
        recommendations.append(f"Engage with top influencer: {top_influencer}")

    if key_topics:
        recommendations.append(f"Create content around trending topics: {', '.join(key_topics[:3])}")

    # Create comprehensive bullets
    bullets = [
        f"Total social mentions: {total_mentions} across {len(platform_insights)} platforms.",
        f"Overall sentiment: {overall_sentiment:.2f} ({'positive' if overall_sentiment > 0 else 'negative'})",
        f"Top platform: {top_platform} with {top_insight.mention_count} mentions ({top_insight.sentiment_trend} trend).",
        f"Sentiment distribution: {positive_count} positive, {negative_count} negative, {neutral_count} neutral.",
    ]

    if influencer_analysis:
        top_influencers = list(influencer_analysis.keys())[:3]
        bullets.append(f"Top influencers: {', '.join(top_influencers)}")

    if key_topics:
        bullets.append(f"Trending topics: {', '.join(key_topics[:3])}")

    # Create metrics
    metrics = {
        "total_mentions": total_mentions,
        "overall_sentiment": round(overall_sentiment, 2),
        "positive_mentions": positive_count,
        "negative_mentions": negative_count,
        "neutral_mentions": neutral_count,
        "platform_count": len(platform_insights),
        "top_platform": top_platform,
        "top_influencer": list(influencer_analysis.keys())[0] if influencer_analysis else "",
        "avg_velocity": round(mean(insight.velocity for insight in platform_insights.values()), 2),
    }

    return WorkerOutput(
        worker="social",
        title="Social listening",
        summary=f"Social analysis shows {total_mentions} mentions with {overall_sentiment:.2f} overall sentiment.",
        bullets=bullets,
        metrics=metrics,
        confidence=0.85,
    )


def create_social_data(worker_output: WorkerOutput) -> SocialData:
    """Create structured social data from worker output."""
    metrics = worker_output.metrics

    # Create sentiment distribution
    sentiment_distribution = {
        "positive": metrics.get("positive_mentions", 0),
        "negative": metrics.get("negative_mentions", 0),
        "neutral": metrics.get("neutral_mentions", 0),
    }

    # Create platform insights (simplified)
    platform_insights = {}
    top_platform = metrics.get("top_platform", "unknown")
    if top_platform != "unknown":
        platform_insights[top_platform] = SocialInsight(
            platform=top_platform,
            mention_count=metrics.get("total_mentions", 0),
            sentiment_score=metrics.get("overall_sentiment", 0.0),
            sentiment_trend="stable",
            top_influencers=[],
            key_topics=[],
            velocity=metrics.get("avg_velocity", 0.0),
            engagement_rate=0.0,  # Default engagement rate
        )

    return SocialData(
        total_mentions=metrics.get("total_mentions", 0),
        overall_sentiment=metrics.get("overall_sentiment", 0.0),
        sentiment_distribution=sentiment_distribution,
        platform_insights=platform_insights,
        top_mentions=[],
        influencer_analysis={},
        trend_analysis="",
        recommendations=[],
    )