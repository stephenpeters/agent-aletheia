"""Unit tests for ChatService."""

import pytest
from uuid import UUID
from agent_sdk.models.chat import (
    ChatRequest,
    FeedbackRequest,
    FeedbackType,
    MessageRole,
)
from agent_aletheia.services.chat import ChatService


@pytest.fixture
def chat_service():
    """Create a ChatService instance for testing."""
    return ChatService()


@pytest.mark.asyncio
async def test_create_session(chat_service):
    """Test session creation."""
    session = await chat_service.create_session()

    assert session.id is not None
    assert isinstance(session.id, UUID)
    assert session.is_active is True
    assert session.message_count == 0
    assert session.ideas_generated == 0
    assert len(session.topics) == 0


@pytest.mark.asyncio
async def test_create_session_with_user_id(chat_service):
    """Test session creation with user ID."""
    user_id = "test_user_123"
    session = await chat_service.create_session(user_id=user_id)

    assert session.user_id == user_id
    assert session.is_active is True


@pytest.mark.asyncio
async def test_get_session(chat_service):
    """Test session retrieval."""
    session = await chat_service.create_session()
    retrieved = await chat_service.get_session(session.id)

    assert retrieved is not None
    assert retrieved.id == session.id


@pytest.mark.asyncio
async def test_get_nonexistent_session(chat_service):
    """Test retrieval of non-existent session."""
    from uuid import uuid4

    session = await chat_service.get_session(uuid4())
    assert session is None


@pytest.mark.asyncio
async def test_send_message_creates_session(chat_service):
    """Test that sending a message without session_id creates a new session."""
    request = ChatRequest(message="Hello Aletheia")

    response = await chat_service.send_message(request)

    assert response.session_id is not None
    assert response.content is not None
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_send_message_to_existing_session(chat_service):
    """Test sending messages to an existing session."""
    session = await chat_service.create_session()

    request1 = ChatRequest(session_id=session.id, message="First message")
    response1 = await chat_service.send_message(request1)

    request2 = ChatRequest(session_id=session.id, message="Second message")
    response2 = await chat_service.send_message(request2)

    # Both responses should have same session_id
    assert response1.session_id == session.id
    assert response2.session_id == session.id

    # Session should have 4 messages (2 user + 2 assistant)
    updated_session = await chat_service.get_session(session.id)
    assert updated_session.message_count == 4


@pytest.mark.asyncio
async def test_send_message_with_invalid_session(chat_service):
    """Test sending message to non-existent session."""
    from uuid import uuid4

    request = ChatRequest(session_id=uuid4(), message="Test")

    with pytest.raises(ValueError):
        await chat_service.send_message(request)


@pytest.mark.asyncio
async def test_message_history(chat_service):
    """Test message history retrieval."""
    session = await chat_service.create_session()

    # Send a few messages
    for i in range(3):
        request = ChatRequest(session_id=session.id, message=f"Message {i}")
        await chat_service.send_message(request)

    # Get history
    history = await chat_service.get_session_history(session.id)

    assert history is not None
    assert history.session.id == session.id
    assert len(history.messages) == 6  # 3 user + 3 assistant messages


@pytest.mark.asyncio
async def test_topic_extraction(chat_service):
    """Test that topics are extracted from messages."""
    request = ChatRequest(
        message="Tell me about AI and tokenized deposits for business strategy",
        topics=["liquidity"],
    )

    response = await chat_service.send_message(request)

    # Check session has topics
    session = await chat_service.get_session(response.session_id)
    assert len(session.topics) > 0
    assert "liquidity" in session.topics  # Explicit topic


@pytest.mark.asyncio
async def test_context_window(chat_service):
    """Test context window management."""
    session = await chat_service.create_session()

    # Send more messages than context window
    for i in range(15):
        request = ChatRequest(
            session_id=session.id, message=f"Message {i}", context_window=10
        )
        await chat_service.send_message(request)

    # History should contain all messages
    history = await chat_service.get_session_history(session.id)
    assert len(history.messages) == 30  # 15 user + 15 assistant


@pytest.mark.asyncio
async def test_list_sessions(chat_service):
    """Test session listing."""
    # Create multiple sessions
    session1 = await chat_service.create_session(user_id="user1")
    session2 = await chat_service.create_session(user_id="user2")
    session3 = await chat_service.create_session(user_id="user1")

    # List all sessions
    result = await chat_service.list_sessions()
    assert result.total == 3
    assert result.active_count == 3

    # List sessions for user1
    result = await chat_service.list_sessions(user_id="user1")
    assert result.total == 2

    # Close a session
    session1.is_active = False

    # List active only
    result = await chat_service.list_sessions(active_only=True)
    assert result.active_count == 2


@pytest.mark.asyncio
async def test_submit_feedback_accept(chat_service):
    """Test accepting an idea via feedback."""
    from uuid import uuid4

    session = await chat_service.create_session()
    idea_id = uuid4()

    feedback = FeedbackRequest(
        session_id=session.id, idea_id=idea_id, feedback_type=FeedbackType.ACCEPT
    )

    response = await chat_service.submit_feedback(feedback)

    assert response.success is True
    assert "recorded" in response.message.lower()

    # Check session statistics
    updated_session = await chat_service.get_session(session.id)
    assert updated_session.ideas_accepted == 1
    assert updated_session.ideas_generated == 1


@pytest.mark.asyncio
async def test_submit_feedback_reject(chat_service):
    """Test rejecting an idea via feedback."""
    from uuid import uuid4

    session = await chat_service.create_session()
    idea_id = uuid4()

    feedback = FeedbackRequest(
        session_id=session.id, idea_id=idea_id, feedback_type=FeedbackType.REJECT
    )

    response = await chat_service.submit_feedback(feedback)

    assert response.success is True

    # Check session statistics
    updated_session = await chat_service.get_session(session.id)
    assert updated_session.ideas_rejected == 1
    assert updated_session.ideas_generated == 1


@pytest.mark.asyncio
async def test_submit_feedback_invalid_session(chat_service):
    """Test feedback submission to non-existent session."""
    from uuid import uuid4

    feedback = FeedbackRequest(
        session_id=uuid4(), idea_id=uuid4(), feedback_type=FeedbackType.ACCEPT
    )

    response = await chat_service.submit_feedback(feedback)

    assert response.success is False
    assert "not found" in response.message.lower()


@pytest.mark.asyncio
async def test_context_confidence_tracking(chat_service):
    """Test that context confidence is tracked."""
    request = ChatRequest(message="Test message")
    response = await chat_service.send_message(request)

    assert response.context_confidence >= 0.0
    assert response.context_confidence <= 1.0

    session = await chat_service.get_session(response.session_id)
    assert session.context_confidence >= 0.0
    assert session.context_confidence <= 1.0


@pytest.mark.asyncio
async def test_latency_tracking(chat_service):
    """Test that response latency is tracked."""
    request = ChatRequest(message="Test message")
    response = await chat_service.send_message(request)

    assert response.latency_ms is not None
    assert response.latency_ms > 0


@pytest.mark.asyncio
async def test_session_touch_updates_timestamp(chat_service):
    """Test that session is touched on updates."""
    session = await chat_service.create_session()
    original_updated_at = session.updated_at

    # Send a message (should touch the session)
    request = ChatRequest(session_id=session.id, message="Test")
    await chat_service.send_message(request)

    updated_session = await chat_service.get_session(session.id)
    assert updated_session.updated_at > original_updated_at
    assert updated_session.last_message_at is not None
