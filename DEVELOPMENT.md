# Aletheia Development Guide

## Setup Complete ✅

- ✅ Package structure created (`agent_aletheia/`)
- ✅ `pyproject.toml` configured with dependencies
- ✅ `requirements.txt` with agent-sdk reference
- ✅ `topics.yaml` configuration file
- ✅ Test directories created

## Next Implementation Steps

### 1. Configuration Loader (`agent_aletheia/config/__init__.py`)

```python
import yaml
from pathlib import Path
from pydantic import BaseModel

class TopicConfig(BaseModel):
    name: str
    keywords: list[str]
    weight: float
    subtopics: list[str] = []

class ScoringConfig(BaseModel):
    novelty_weight: float = 0.4
    topicality_weight: float = 0.3
    relevance_weight: float = 0.3
    minimum_score: float = 0.65

class AletheiaConfig(BaseModel):
    primary_topics: list[TopicConfig]
    secondary_topics: list[TopicConfig]
    exclude_topics: list[str]
    scoring: ScoringConfig

def load_config() -> AletheiaConfig:
    config_path = Path(__file__).parent / "topics.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)

    return AletheiaConfig(
        primary_topics=[TopicConfig(**t) for t in data['topics']['primary']],
        secondary_topics=[TopicConfig(**t) for t in data['topics'].get('secondary', [])],
        exclude_topics=data['topics'].get('exclude', []),
        scoring=ScoringConfig(**data['scoring'])
    )
```

### 2. Content Ingestion Service (`agent_aletheia/services/ingestion.py`)

```python
from agent_sdk.models import SourceType
import httpx
from bs4 import BeautifulSoup
import feedparser
from PyPDF2 import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi

class ContentIngestionService:
    async def ingest_url(self, url: str) -> dict:
        """Fetch and parse content from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title and content
            title = soup.find('title').text if soup.find('title') else ""
            # Remove scripts, styles
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text()

            return {
                "title": title,
                "content": text,
                "url": url
            }

    async def ingest_rss(self, feed_url: str) -> list[dict]:
        """Parse RSS feed and return entries."""
        feed = feedparser.parse(feed_url)
        return [
            {
                "title": entry.title,
                "content": entry.summary,
                "url": entry.link,
                "published": entry.published
            }
            for entry in feed.entries
        ]

    def ingest_pdf(self, pdf_path: str) -> dict:
        """Extract text from PDF."""
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        return {
            "title": pdf_path,
            "content": text
        }

    def ingest_youtube(self, video_id: str) -> dict:
        """Get YouTube transcript."""
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'] for entry in transcript])

        return {
            "title": f"YouTube: {video_id}",
            "content": text,
            "url": f"https://youtube.com/watch?v={video_id}"
        }
```

### 3. Idea Scoring Service (`agent_aletheia/services/scoring.py`)

```python
from agent_sdk.models import IdeaModel, IdeaScore
from agent_aletheia.config import AletheiaConfig
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class IdeaScoringService:
    def __init__(self, config: AletheiaConfig):
        self.config = config

    def score_idea(self, idea: IdeaModel) -> IdeaScore:
        """Score an idea based on novelty, topicality, and relevance."""
        novelty = self._calculate_novelty(idea)
        topicality = self._calculate_topicality(idea)
        relevance = self._calculate_relevance(idea)

        overall = (
            novelty * self.config.scoring.novelty_weight +
            topicality * self.config.scoring.topicality_weight +
            relevance * self.config.scoring.relevance_weight
        )

        return IdeaScore(
            novelty=novelty,
            topicality=topicality,
            relevance=relevance,
            overall=overall
        )

    def _calculate_relevance(self, idea: IdeaModel) -> float:
        """Calculate relevance to configured topics."""
        content_lower = (idea.title + " " + idea.summary).lower()

        max_relevance = 0.0
        for topic in self.config.primary_topics:
            keyword_matches = sum(
                1 for keyword in topic.keywords
                if keyword.lower() in content_lower
            )
            topic_relevance = (keyword_matches / len(topic.keywords)) * topic.weight
            max_relevance = max(max_relevance, topic_relevance)

        # Check exclusions
        for exclusion in self.config.exclude_topics:
            if exclusion.lower() in content_lower:
                return 0.0

        return min(max_relevance, 1.0)

    def _calculate_novelty(self, idea: IdeaModel) -> float:
        """Calculate novelty (placeholder - needs Mnemosyne integration)."""
        # TODO: Check against existing ideas in Mnemosyne
        # For now, return a random score
        return 0.7

    def _calculate_topicality(self, idea: IdeaModel) -> float:
        """Calculate topicality/trending (placeholder)."""
        # TODO: Implement trending detection
        return 0.6
```

### 4. FastAPI Routes (`agent_aletheia/routes/ideas.py`)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from agent_sdk.models import IdeaModel, SourceType
from agent_aletheia.services.ingestion import ContentIngestionService
from agent_aletheia.services.scoring import IdeaScoringService
from agent_aletheia.config import load_config

router = APIRouter(prefix="/v1")

class IngestRequest(BaseModel):
    url: HttpUrl
    source_type: SourceType = SourceType.URL

config = load_config()
ingestion_service = ContentIngestionService()
scoring_service = IdeaScoringService(config)

@router.post("/ingest")
async def ingest_content(request: IngestRequest):
    """Ingest content from a URL."""
    if request.source_type == SourceType.URL:
        data = await ingestion_service.ingest_url(str(request.url))
    else:
        raise HTTPException(400, "Source type not yet implemented")

    return {
        "status": "processing",
        "data": data
    }

@router.post("/ideas/generate")
async def generate_idea(content: dict):
    """Generate and score an idea from content."""
    idea = IdeaModel(
        title=content["title"],
        summary=content.get("summary", content["content"][:500]),
        content=content["content"],
        source_type=SourceType.URL,
        source_url=content.get("url")
    )

    # Score the idea
    idea.score = scoring_service.score_idea(idea)

    # Check threshold
    if idea.is_above_threshold(config.scoring.minimum_score):
        idea.approve()

    return idea

@router.get("/ideas/{idea_id}")
async def get_idea(idea_id: str):
    """Get an idea by ID."""
    # TODO: Implement database retrieval
    raise HTTPException(501, "Not yet implemented")
```

### 5. Update main.py

```python
from fastapi import FastAPI
from agent_aletheia.routes import ideas
from agent_sdk.utils import setup_logger

logger = setup_logger("agent-aletheia")

app = FastAPI(
    title="Aletheia",
    description="Idea Discovery Agent",
    version="0.1.0"
)

app.include_router(ideas.router)

@app.get("/healthz")
def health_check():
    return {"status": "ok", "agent": "agent-aletheia"}

@app.on_event("startup")
async def startup():
    logger.info("Aletheia starting up")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Aletheia shutting down")
```

## Installation & Running

```bash
# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --port 8001
```

## Testing

```bash
# Test health endpoint
curl http://localhost:8001/healthz

# Test ingestion
curl -X POST http://localhost:8001/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

## Next Week Tasks

1. Implement database layer (Postgres + SQLAlchemy)
2. Add Mnemosyne integration for novelty checking
3. Improve scoring algorithms
4. Add comprehensive tests
5. Implement remaining source types (RSS, PDF, YouTube)
