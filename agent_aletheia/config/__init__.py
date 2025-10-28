"""Configuration management for Aletheia."""

import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class TopicConfig(BaseModel):
    """Configuration for a single topic."""
    name: str
    keywords: list[str]
    weight: float
    subtopics: list[str] = []


class ScoringConfig(BaseModel):
    """Scoring weights and thresholds."""
    novelty_weight: float = 0.4
    topicality_weight: float = 0.3
    relevance_weight: float = 0.3
    minimum_score: float = 0.65


class FilterConfig(BaseModel):
    """Content filtering configuration."""
    min_content_length: int = 500
    max_age_days: int = 7
    languages: list[str] = ["en"]


class AletheiaConfig(BaseModel):
    """Main configuration for Aletheia agent."""
    primary_topics: list[TopicConfig]
    secondary_topics: list[TopicConfig]
    exclude_topics: list[str]
    scoring: ScoringConfig
    filters: FilterConfig


def load_config(config_path: Optional[Path] = None) -> AletheiaConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Optional path to config file. Defaults to topics.yaml in this directory.

    Returns:
        AletheiaConfig instance
    """
    if config_path is None:
        config_path = Path(__file__).parent / "topics.yaml"

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return AletheiaConfig(
        primary_topics=[TopicConfig(**t) for t in data['topics']['primary']],
        secondary_topics=[TopicConfig(**t) for t in data['topics'].get('secondary', [])],
        exclude_topics=data['topics'].get('exclude', []),
        scoring=ScoringConfig(**data['scoring']),
        filters=FilterConfig(**data.get('filters', {}))
    )
