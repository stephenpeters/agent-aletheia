"""Idea scoring service for Aletheia."""

from typing import Optional
from agent_sdk.models.idea import IdeaModel, IdeaScore
from agent_sdk.utils import setup_logger
from agent_aletheia.config import AletheiaConfig, load_config

logger = setup_logger("aletheia.scoring")


class IdeaScoringService:
    """Service for scoring ideas based on relevance, novelty, and topicality."""

    def __init__(self, config: Optional[AletheiaConfig] = None):
        self.config = config or load_config()
        self.primary_topics = self.config.primary_topics
        self.secondary_topics = self.config.secondary_topics
        self.exclude_topics = self.config.exclude_topics
        self.scoring_config = self.config.scoring

    async def score_idea(self, idea: IdeaModel) -> IdeaScore:
        """
        Score an idea based on relevance, novelty, and topicality.

        Args:
            idea: The idea to score

        Returns:
            IdeaScore with calculated scores
        """
        logger.info("Scoring idea", extra={"idea_id": str(idea.id), "title": idea.title})

        # Calculate component scores
        relevance = self._calculate_relevance(idea)
        novelty = await self._calculate_novelty(idea)
        topicality = self._calculate_topicality(idea)

        # Calculate weighted composite score
        composite = (
            relevance * self.scoring_config.relevance_weight
            + novelty * self.scoring_config.novelty_weight
            + topicality * self.scoring_config.topicality_weight
        )

        score = IdeaScore(
            idea_id=idea.id,
            relevance_score=relevance,
            novelty_score=novelty,
            topicality_score=topicality,
            composite_score=composite,
        )

        logger.info(
            "Idea scored",
            extra={
                "idea_id": str(idea.id),
                "composite_score": composite,
                "relevance": relevance,
                "novelty": novelty,
                "topicality": topicality,
            },
        )

        return score

    def _calculate_relevance(self, idea: IdeaModel) -> float:
        """
        Calculate relevance score based on keyword matching.

        Args:
            idea: The idea to score

        Returns:
            Relevance score between 0 and 1
        """
        content_lower = f"{idea.title} {idea.content}".lower()

        # Check for excluded topics first
        for excluded in self.exclude_topics:
            if excluded.lower() in content_lower:
                logger.debug(
                    "Idea contains excluded topic",
                    extra={"idea_id": str(idea.id), "excluded_topic": excluded},
                )
                return 0.0

        # Calculate primary topic matches
        primary_score = 0.0
        primary_matches = []
        for topic in self.primary_topics:
            matches = sum(
                1 for keyword in topic.keywords if keyword.lower() in content_lower
            )
            if matches > 0:
                primary_matches.append(topic.name)
                # Score based on number of keyword matches and topic weight
                topic_score = min(matches / len(topic.keywords), 1.0) * topic.weight
                primary_score = max(primary_score, topic_score)

        # Calculate secondary topic matches
        secondary_score = 0.0
        secondary_matches = []
        for topic in self.secondary_topics:
            matches = sum(
                1 for keyword in topic.keywords if keyword.lower() in content_lower
            )
            if matches > 0:
                secondary_matches.append(topic.name)
                topic_score = min(matches / len(topic.keywords), 1.0) * topic.weight
                secondary_score = max(secondary_score, topic_score)

        # Combine scores (primary weighted higher)
        relevance = primary_score * 0.7 + secondary_score * 0.3

        logger.debug(
            "Relevance calculated",
            extra={
                "idea_id": str(idea.id),
                "relevance": relevance,
                "primary_matches": primary_matches,
                "secondary_matches": secondary_matches,
            },
        )

        return min(relevance, 1.0)

    async def _calculate_novelty(self, idea: IdeaModel) -> float:
        """
        Calculate novelty score by checking against existing ideas.

        TODO: Integrate with Mnemosyne to check semantic similarity
        against previously discovered ideas.

        Args:
            idea: The idea to score

        Returns:
            Novelty score between 0 and 1
        """
        # Placeholder implementation
        # In full implementation, this would:
        # 1. Query Mnemosyne for similar ideas using semantic search
        # 2. Calculate similarity scores
        # 3. Return novelty based on uniqueness

        logger.debug(
            "Novelty calculation (placeholder)",
            extra={"idea_id": str(idea.id), "novelty": 0.8},
        )

        return 0.8  # Default to high novelty until Mnemosyne integration

    def _calculate_topicality(self, idea: IdeaModel) -> float:
        """
        Calculate topicality score based on content freshness and trends.

        TODO: Integrate with trend detection system to identify
        emerging topics and patterns.

        Args:
            idea: The idea to score

        Returns:
            Topicality score between 0 and 1
        """
        # Placeholder implementation
        # In full implementation, this would:
        # 1. Check publication date recency
        # 2. Analyze trending keywords
        # 3. Compare against recent topic patterns

        logger.debug(
            "Topicality calculation (placeholder)",
            extra={"idea_id": str(idea.id), "topicality": 0.7},
        )

        return 0.7  # Default to moderate topicality

    def passes_minimum_threshold(self, score: IdeaScore) -> bool:
        """
        Check if idea score passes minimum threshold.

        Args:
            score: The idea score to check

        Returns:
            True if score meets or exceeds minimum threshold
        """
        passes = score.composite_score >= self.scoring_config.minimum_score
        logger.debug(
            "Threshold check",
            extra={
                "idea_id": str(score.idea_id),
                "composite_score": score.composite_score,
                "minimum_score": self.scoring_config.minimum_score,
                "passes": passes,
            },
        )
        return passes
