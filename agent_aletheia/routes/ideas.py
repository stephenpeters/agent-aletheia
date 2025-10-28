"""API routes for idea management."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl, Field
from agent_sdk.models.idea import IdeaModel, IdeaScore, SourceType, IdeaStatus
from agent_sdk.utils import setup_logger
from agent_aletheia.services.ingestion import ContentIngestionService
from agent_aletheia.services.scoring import IdeaScoringService

logger = setup_logger("aletheia.routes")

router = APIRouter(prefix="/ideas", tags=["ideas"])

# Initialize services
ingestion_service = ContentIngestionService()
scoring_service = IdeaScoringService()


class IngestURLRequest(BaseModel):
    """Request model for URL ingestion."""

    url: HttpUrl
    source_name: Optional[str] = None


class IngestRSSRequest(BaseModel):
    """Request model for RSS feed ingestion."""

    feed_url: HttpUrl
    max_entries: int = Field(default=10, ge=1, le=50)


class IngestYouTubeRequest(BaseModel):
    """Request model for YouTube ingestion."""

    video_id: str = Field(..., min_length=11, max_length=11)


class ManualIdeaRequest(BaseModel):
    """Request model for manual idea submission."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=100)
    source_name: Optional[str] = "Manual Entry"
    tags: list[str] = Field(default_factory=list)


class IdeaResponse(BaseModel):
    """Response model for idea with score."""

    idea: IdeaModel
    score: IdeaScore
    passes_threshold: bool


@router.post("/ingest/url", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def ingest_url(request: IngestURLRequest):
    """
    Ingest content from a URL and create an idea.

    This endpoint:
    1. Fetches and parses the URL content
    2. Creates an IdeaModel
    3. Scores the idea
    4. Returns the idea with its score
    """
    try:
        # Ingest content
        content_data = await ingestion_service.ingest_url(str(request.url))

        # Create idea
        idea = IdeaModel(
            title=content_data["title"],
            content=content_data["content"],
            source_type=SourceType.URL,
            source_url=content_data["url"],
            source_name=request.source_name or content_data["url"],
            word_count=content_data["word_count"],
        )

        # Score idea
        score = await scoring_service.score_idea(idea)
        passes = scoring_service.passes_minimum_threshold(score)

        logger.info(
            "URL ingested and scored",
            extra={
                "idea_id": str(idea.id),
                "url": str(request.url),
                "score": score.composite_score,
                "passes": passes,
            },
        )

        return IdeaResponse(idea=idea, score=score, passes_threshold=passes)

    except Exception as e:
        logger.error("Failed to ingest URL", exc_info=True, extra={"url": str(request.url)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest URL: {str(e)}",
        )


@router.post("/ingest/rss", response_model=list[IdeaResponse])
async def ingest_rss(request: IngestRSSRequest):
    """
    Ingest entries from an RSS feed.

    This endpoint:
    1. Parses the RSS feed
    2. Creates IdeaModels for each entry
    3. Scores each idea
    4. Returns all ideas with scores
    """
    try:
        # Ingest RSS feed
        entries = await ingestion_service.ingest_rss(
            str(request.feed_url), max_entries=request.max_entries
        )

        responses = []
        for entry in entries:
            # Create idea
            idea = IdeaModel(
                title=entry["title"],
                content=entry["content"],
                source_type=SourceType.RSS,
                source_url=entry["url"],
                source_name=str(request.feed_url),
                metadata={
                    "published": entry["published"],
                    "author": entry["author"],
                },
            )

            # Score idea
            score = await scoring_service.score_idea(idea)
            passes = scoring_service.passes_minimum_threshold(score)

            responses.append(IdeaResponse(idea=idea, score=score, passes_threshold=passes))

        logger.info(
            "RSS feed ingested",
            extra={
                "feed_url": str(request.feed_url),
                "entries_count": len(responses),
                "passed_count": sum(1 for r in responses if r.passes_threshold),
            },
        )

        return responses

    except Exception as e:
        logger.error(
            "Failed to ingest RSS feed",
            exc_info=True,
            extra={"feed_url": str(request.feed_url)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest RSS feed: {str(e)}",
        )


@router.post("/ingest/youtube", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def ingest_youtube(request: IngestYouTubeRequest):
    """
    Ingest content from a YouTube video transcript.

    This endpoint:
    1. Fetches the video transcript
    2. Creates an IdeaModel
    3. Scores the idea
    4. Returns the idea with its score
    """
    try:
        # Ingest YouTube video
        content_data = await ingestion_service.ingest_youtube(request.video_id)

        # Create idea
        idea = IdeaModel(
            title=content_data["title"],
            content=content_data["content"],
            source_type=SourceType.YOUTUBE,
            source_url=content_data["url"],
            source_name=f"YouTube: {request.video_id}",
            word_count=content_data["word_count"],
            metadata={"video_id": content_data["video_id"]},
        )

        # Score idea
        score = await scoring_service.score_idea(idea)
        passes = scoring_service.passes_minimum_threshold(score)

        logger.info(
            "YouTube video ingested and scored",
            extra={
                "idea_id": str(idea.id),
                "video_id": request.video_id,
                "score": score.composite_score,
                "passes": passes,
            },
        )

        return IdeaResponse(idea=idea, score=score, passes_threshold=passes)

    except Exception as e:
        logger.error(
            "Failed to ingest YouTube video",
            exc_info=True,
            extra={"video_id": request.video_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest YouTube video: {str(e)}",
        )


@router.post("/manual", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_idea(request: ManualIdeaRequest):
    """
    Create an idea manually without ingestion.

    This endpoint:
    1. Creates an IdeaModel from provided data
    2. Scores the idea
    3. Returns the idea with its score
    """
    try:
        # Create idea
        idea = IdeaModel(
            title=request.title,
            content=request.content,
            source_type=SourceType.MANUAL,
            source_name=request.source_name,
            tags=request.tags,
        )

        # Score idea
        score = await scoring_service.score_idea(idea)
        passes = scoring_service.passes_minimum_threshold(score)

        logger.info(
            "Manual idea created and scored",
            extra={
                "idea_id": str(idea.id),
                "title": idea.title,
                "score": score.composite_score,
                "passes": passes,
            },
        )

        return IdeaResponse(idea=idea, score=score, passes_threshold=passes)

    except Exception as e:
        logger.error("Failed to create manual idea", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create manual idea: {str(e)}",
        )


@router.post("/{idea_id}/approve", status_code=status.HTTP_200_OK)
async def approve_idea(idea_id: UUID):
    """
    Approve an idea for processing by IRIS.

    TODO: Integrate with database to persist idea approval
    and emit event to IRIS via Mnemosyne.
    """
    logger.info("Idea approved", extra={"idea_id": str(idea_id)})
    return {"message": "Idea approved", "idea_id": str(idea_id)}


@router.post("/{idea_id}/reject", status_code=status.HTTP_200_OK)
async def reject_idea(idea_id: UUID, reason: Optional[str] = None):
    """
    Reject an idea.

    TODO: Integrate with database to persist idea rejection.
    """
    logger.info(
        "Idea rejected",
        extra={"idea_id": str(idea_id), "reason": reason or "Not specified"},
    )
    return {"message": "Idea rejected", "idea_id": str(idea_id), "reason": reason}


@router.on_event("shutdown")
async def shutdown_event():
    """Clean up services on shutdown."""
    await ingestion_service.close()
