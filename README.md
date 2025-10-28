# Aletheia – Idea Discovery Agent

**Mission**: Identify, evaluate, and summarize potential content ideas from structured and unstructured data sources.

## Core Capabilities

- Ingest URLs, RSS feeds, PDFs, and YouTube transcripts
- Summarize articles into concise briefs
- Score ideas by novelty, topicality, and relevance
- Detect trends and cluster related ideas

## API Endpoints

- `POST /v1/ingest` - Ingest content from various sources
- `POST /v1/ideas/generate` - Generate and score content ideas
- `GET /v1/ideas/{id}` - Retrieve specific idea details
- `GET /healthz` - Health check endpoint

## Key Deliverables

- `idea.json` schema defining standardized idea format
- FastAPI service with content ingestion and idea generation
- Integration with Mnemosyne context API for relevance checks

## Dependencies

- Python 3.11+
- FastAPI, uvicorn
- LangChain or Anthropic SDK for summarization
- Postgres + pgvector for idea embeddings
- Integration with Mnemosyne context API

## Development

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the service
uvicorn main:app --reload --port 8001

# Install additional dependencies
pip install <package>
pip freeze > requirements.txt
```

## Data Flow

Aletheia is the first agent in the pipeline:

```
External Sources → Aletheia → IRIS
                       ↓
                   Mnemosyne (context check)
```

## Related Repositories

- [agent-iris](https://github.com/stephenpeters/agent-iris) - Receives ideas for drafting
- [agent-mnemosyne](https://github.com/stephenpeters/agent-mnemosyne) - Provides context for relevance scoring
- [agent-sdk](https://github.com/stephenpeters/agent-sdk) - Shared schemas and utilities
