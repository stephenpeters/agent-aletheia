"""API routes for chat interface."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from agent_sdk.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatSession,
    FeedbackRequest,
    FeedbackResponse,
    SessionHistoryResponse,
    SessionListResponse,
)
from agent_sdk.utils import setup_logger
from agent_aletheia.services.chat import ChatService

logger = setup_logger("aletheia.routes.chat")

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize chat service
chat_service = ChatService()


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(request: ChatRequest):
    """
    Send a message to Aletheia and get a response.

    This endpoint:
    1. Creates a new session if session_id is null
    2. Adds user message to conversation history
    3. Queries Mnemosyne for relevant context (if available)
    4. Generates Aletheia's response using Claude
    5. Optionally searches for and suggests relevant ideas
    6. Returns response with context confidence score

    KPI Target: Response latency < 500ms
    """
    try:
        response = await chat_service.send_message(request)

        logger.info(
            "Chat message processed",
            extra={
                "session_id": str(response.session_id),
                "latency_ms": response.latency_ms,
                "ideas_count": len(response.ideas),
            },
        )

        return response

    except ValueError as e:
        logger.error("Invalid request", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Failed to process message", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post("/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
async def create_session(user_id: Optional[str] = None):
    """
    Create a new chat session.

    Args:
        user_id: Optional user identifier

    Returns:
        New ChatSession
    """
    try:
        session = await chat_service.create_session(user_id=user_id)

        logger.info("Session created", extra={"session_id": str(session.id)})

        return session

    except Exception as e:
        logger.error("Failed to create session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(user_id: Optional[str] = None, active_only: bool = False):
    """
    List all chat sessions.

    Args:
        user_id: Optional filter by user ID
        active_only: Only return active sessions

    Returns:
        SessionListResponse with list of sessions
    """
    try:
        response = await chat_service.list_sessions(user_id=user_id, active_only=active_only)

        logger.debug(
            "Sessions listed",
            extra={
                "total": response.total,
                "active_count": response.active_count,
            },
        )

        return response

    except Exception as e:
        logger.error("Failed to list sessions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(session_id: UUID):
    """
    Get full history of a chat session.

    Args:
        session_id: Session identifier

    Returns:
        SessionHistoryResponse with session and all messages
    """
    try:
        history = await chat_service.get_session_history(session_id)

        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        logger.debug(
            "Session history retrieved",
            extra={
                "session_id": str(session_id),
                "message_count": len(history.messages),
            },
        )

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get session history",
            exc_info=True,
            extra={"session_id": str(session_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session history: {str(e)}",
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit feedback on an idea (accept/reject/flag).

    This endpoint:
    1. Records user feedback on an idea
    2. Updates session statistics
    3. Queues feedback for Mnemosyne learning (future)
    4. Returns updated context confidence

    Args:
        feedback: FeedbackRequest with session_id, idea_id, and feedback_type

    Returns:
        FeedbackResponse confirming feedback recorded
    """
    try:
        response = await chat_service.submit_feedback(feedback)

        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.message,
            )

        logger.info(
            "Feedback submitted",
            extra={
                "session_id": str(feedback.session_id),
                "idea_id": str(feedback.idea_id),
                "feedback_type": feedback.feedback_type.value,
            },
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit feedback", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}",
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_session(session_id: UUID):
    """
    Close (deactivate) a chat session.

    Args:
        session_id: Session identifier

    Returns:
        204 No Content on success
    """
    try:
        session = await chat_service.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        session.is_active = False
        session.touch()

        logger.info("Session closed", extra={"session_id": str(session_id)})

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to close session",
            exc_info=True,
            extra={"session_id": str(session_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close session: {str(e)}",
        )


@router.on_event("shutdown")
async def shutdown_event():
    """Clean up chat service on shutdown."""
    logger.info("Chat service shutting down")
    # TODO: Persist sessions to database before shutdown
