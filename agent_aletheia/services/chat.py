"""Chat service for Aletheia conversational interface."""

import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from agent_sdk.models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSession,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackType,
    IdeaSuggestion,
    MessageRole,
    SessionHistoryResponse,
    SessionListResponse,
)
from agent_sdk.models.idea import IdeaModel
from agent_sdk.models.memory import QueryRequest, ContextDepth
from agent_sdk.utils import setup_logger

logger = setup_logger("aletheia.chat")


class ChatService:
    """Service for managing chat sessions and conversations with Aletheia."""

    def __init__(self):
        # In-memory storage for MVP (replace with database later)
        self.sessions: dict[UUID, ChatSession] = {}
        self.messages: dict[UUID, list[ChatMessage]] = {}  # session_id -> messages
        self.ideas_cache: dict[UUID, IdeaModel] = {}  # idea_id -> IdeaModel

        # TODO: Initialize Mnemosyne client once implemented
        self.mnemosyne_client = None

        logger.info("ChatService initialized")

    async def create_session(self, user_id: Optional[str] = None) -> ChatSession:
        """
        Create a new chat session.

        Args:
            user_id: Optional user identifier

        Returns:
            New ChatSession
        """
        session = ChatSession(user_id=user_id)
        self.sessions[session.id] = session
        self.messages[session.id] = []

        logger.info("New session created", extra={"session_id": str(session.id)})
        return session

    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            ChatSession if found, None otherwise
        """
        return self.sessions.get(session_id)

    async def list_sessions(
        self, user_id: Optional[str] = None, active_only: bool = False
    ) -> SessionListResponse:
        """
        List all sessions, optionally filtered.

        Args:
            user_id: Filter by user ID
            active_only: Only return active sessions

        Returns:
            SessionListResponse with list of sessions
        """
        sessions = list(self.sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        if active_only:
            sessions = [s for s in sessions if s.is_active]

        active_count = sum(1 for s in sessions if s.is_active)

        return SessionListResponse(
            sessions=sessions, total=len(sessions), active_count=active_count
        )

    async def get_session_history(self, session_id: UUID) -> Optional[SessionHistoryResponse]:
        """
        Get full history of a session.

        Args:
            session_id: Session identifier

        Returns:
            SessionHistoryResponse with session and messages
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        messages = self.messages.get(session_id, [])

        # Collect all referenced idea IDs
        idea_refs = set()
        for msg in messages:
            idea_refs.update(msg.idea_refs)

        return SessionHistoryResponse(
            session=session, messages=messages, ideas_referenced=list(idea_refs)
        )

    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a user message and generate Aletheia's response.

        Args:
            request: ChatRequest with message and context

        Returns:
            ChatResponse with assistant's reply
        """
        start_time = time.time()

        # Get or create session
        if request.session_id:
            session = await self.get_session(request.session_id)
            if not session:
                raise ValueError(f"Session {request.session_id} not found")
        else:
            session = await self.create_session()

        # Store user message
        user_message = ChatMessage(
            session_id=session.id,
            role=MessageRole.USER,
            content=request.message,
            context_confidence=session.context_confidence,
        )
        self.messages[session.id].append(user_message)
        session.increment_message_count()

        # Extract topics from user message (simple keyword extraction for MVP)
        topics = self._extract_topics(request.message, request.topics)
        for topic in topics:
            session.add_topic(topic)

        # Query Mnemosyne for context (if available)
        mnemosyne_available = False
        context_confidence = 0.8  # Default
        if self.mnemosyne_client:
            try:
                # TODO: Query Mnemosyne
                mnemosyne_available = True
                context_confidence = 0.9
            except Exception as e:
                logger.warning(
                    "Mnemosyne unavailable, using cached context",
                    exc_info=True,
                    extra={"session_id": str(session.id)},
                )

        # Generate response using Claude
        response_content = await self._generate_response(
            session, request.message, request.context_window
        )

        # Search for relevant ideas if requested
        ideas = []
        if request.include_ideas:
            ideas = await self._search_ideas(topics, session)

        # Create assistant message
        assistant_message = ChatMessage(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=response_content,
            idea_refs=[idea.idea_id for idea in ideas],
            context_confidence=context_confidence,
        )
        self.messages[session.id].append(assistant_message)
        session.increment_message_count()

        # Update session
        session.context_confidence = context_confidence
        session.touch()

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Message processed",
            extra={
                "session_id": str(session.id),
                "latency_ms": latency_ms,
                "ideas_count": len(ideas),
                "context_confidence": context_confidence,
            },
        )

        return ChatResponse(
            session_id=session.id,
            message_id=assistant_message.id,
            content=response_content,
            ideas=ideas,
            topics_discussed=topics,
            context_confidence=context_confidence,
            mnemosyne_available=mnemosyne_available,
            latency_ms=latency_ms,
        )

    async def submit_feedback(self, feedback: FeedbackRequest) -> FeedbackResponse:
        """
        Process user feedback on an idea.

        Args:
            feedback: FeedbackRequest with idea ID and feedback type

        Returns:
            FeedbackResponse confirming feedback recorded
        """
        session = await self.get_session(feedback.session_id)
        if not session:
            return FeedbackResponse(
                success=False,
                message=f"Session {feedback.session_id} not found",
            )

        # Record feedback in session
        if feedback.feedback_type == FeedbackType.ACCEPT:
            session.record_idea(accepted=True)
        elif feedback.feedback_type == FeedbackType.REJECT:
            session.record_idea(accepted=False)

        # TODO: Push feedback to Mnemosyne for learning

        logger.info(
            "Feedback recorded",
            extra={
                "session_id": str(session.id),
                "idea_id": str(feedback.idea_id),
                "feedback_type": feedback.feedback_type.value,
            },
        )

        return FeedbackResponse(
            success=True,
            message="Feedback recorded successfully",
            updated_context_confidence=session.context_confidence,
        )

    async def _generate_response(
        self, session: ChatSession, message: str, context_window: int
    ) -> str:
        """
        Generate Aletheia's response using Claude.

        Args:
            session: Current chat session
            message: User's message
            context_window: Number of previous messages to include

        Returns:
            Generated response text
        """
        # Get recent message history
        messages = self.messages.get(session.id, [])
        recent_messages = messages[-context_window:] if len(messages) > 0 else []

        # Build context
        context_lines = []
        for msg in recent_messages[:-1]:  # Exclude the current user message
            role = "You" if msg.role == MessageRole.ASSISTANT else "User"
            context_lines.append(f"{role}: {msg.content}")

        context = "\n".join(context_lines) if context_lines else "No prior context"

        # Build prompt for Claude
        prompt = f"""You are Aletheia, an intelligent ideation and reflection agent. You help users discover insights, explore ideas, and think through topics deeply.

Current conversation context:
{context}

Current topics of focus: {', '.join(session.topics) if session.topics else 'None established yet'}

User: {message}

Respond naturally and helpfully. If the user is exploring ideas, suggest relevant directions. If they're seeking summaries or insights, provide clear analysis. Be conversational but insightful."""

        # TODO: Call Claude API
        # For MVP, return a simple response
        response = f"I understand you're interested in {message[:50]}... Let me help you explore this further. "

        if session.topics:
            response += f"Based on our conversation about {', '.join(session.topics[:2])}, I can suggest some related ideas."
        else:
            response += "What specific aspects would you like to explore?"

        return response

    async def _search_ideas(self, topics: list[str], session: ChatSession) -> list[IdeaSuggestion]:
        """
        Search for relevant ideas based on topics.

        Args:
            topics: List of topics to search for
            session: Current chat session

        Returns:
            List of IdeaSuggestion objects
        """
        # TODO: Integrate with idea discovery and Mnemosyne
        # For MVP, return empty list
        logger.debug(
            "Idea search requested",
            extra={"session_id": str(session.id), "topics": topics},
        )
        return []

    def _extract_topics(self, message: str, explicit_topics: list[str]) -> list[str]:
        """
        Extract topics from message (simple keyword extraction for MVP).

        Args:
            message: User's message
            explicit_topics: Topics explicitly provided

        Returns:
            List of identified topics
        """
        topics = list(explicit_topics)

        # Simple keyword extraction (improve with NLP later)
        keywords = [
            "AI",
            "technology",
            "business",
            "liquidity",
            "tokenized",
            "stablecoin",
            "deposits",
            "treasury",
            "commerce",
        ]

        message_lower = message.lower()
        for keyword in keywords:
            if keyword.lower() in message_lower and keyword not in topics:
                topics.append(keyword)

        return topics
