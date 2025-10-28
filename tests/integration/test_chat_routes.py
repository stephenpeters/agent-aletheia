"""Integration tests for chat API routes."""

import pytest
from fastapi.testclient import TestClient
from uuid import UUID
from main import app

client = TestClient(app)


def test_send_message_creates_session():
    """Test POST /chat creates a new session when session_id is null."""
    response = client.post(
        "/chat",
        json={"message": "Hello Aletheia", "include_ideas": False},
    )

    assert response.status_code == 200
    data = response.json()

    assert "session_id" in data
    assert "message_id" in data
    assert "content" in data
    assert len(data["content"]) > 0
    assert "context_confidence" in data
    assert "latency_ms" in data

    # Validate UUIDs
    UUID(data["session_id"])
    UUID(data["message_id"])


def test_send_message_to_existing_session():
    """Test POST /chat with existing session_id."""
    # Create session
    response1 = client.post("/chat", json={"message": "First message"})
    assert response1.status_code == 200
    session_id = response1.json()["session_id"]

    # Send second message to same session
    response2 = client.post(
        "/chat", json={"session_id": session_id, "message": "Second message"}
    )

    assert response2.status_code == 200
    data = response2.json()
    assert data["session_id"] == session_id


def test_send_message_with_explicit_topics():
    """Test POST /chat with explicit topics."""
    response = client.post(
        "/chat",
        json={
            "message": "Tell me about liquidity",
            "topics": ["tokenized deposits", "stablecoins"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "topics_discussed" in data
    assert len(data["topics_discussed"]) > 0


def test_send_message_with_context_window():
    """Test POST /chat with custom context window."""
    response = client.post(
        "/chat", json={"message": "Test message", "context_window": 5}
    )

    assert response.status_code == 200


def test_send_message_with_invalid_session():
    """Test POST /chat with non-existent session_id."""
    import uuid

    response = client.post(
        "/chat",
        json={"session_id": str(uuid.uuid4()), "message": "Test"},
    )

    assert response.status_code == 400


def test_create_session():
    """Test POST /chat/sessions."""
    response = client.post("/chat/sessions")

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert "created_at" in data
    assert "is_active" in data
    assert data["is_active"] is True
    assert data["message_count"] == 0


def test_create_session_with_user_id():
    """Test POST /chat/sessions with user_id."""
    user_id = "test_user_123"
    response = client.post("/chat/sessions", params={"user_id": user_id})

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id


def test_list_sessions():
    """Test GET /chat/sessions."""
    # Create a couple of sessions
    client.post("/chat/sessions")
    client.post("/chat/sessions")

    response = client.get("/chat/sessions")

    assert response.status_code == 200
    data = response.json()

    assert "sessions" in data
    assert "total" in data
    assert "active_count" in data
    assert data["total"] >= 2


def test_list_sessions_with_filters():
    """Test GET /chat/sessions with filters."""
    user_id = "filter_test_user"
    client.post("/chat/sessions", params={"user_id": user_id})

    response = client.get("/chat/sessions", params={"user_id": user_id})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_list_sessions_active_only():
    """Test GET /chat/sessions with active_only filter."""
    response = client.get("/chat/sessions", params={"active_only": True})

    assert response.status_code == 200
    data = response.json()

    # All returned sessions should be active
    for session in data["sessions"]:
        assert session["is_active"] is True


def test_get_session_history():
    """Test GET /chat/sessions/{session_id}."""
    # Create session and send messages
    response1 = client.post("/chat", json={"message": "First message"})
    session_id = response1.json()["session_id"]

    client.post("/chat", json={"session_id": session_id, "message": "Second message"})

    # Get history
    response = client.get(f"/chat/sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()

    assert "session" in data
    assert "messages" in data
    assert "ideas_referenced" in data

    assert data["session"]["id"] == session_id
    assert len(data["messages"]) == 4  # 2 user + 2 assistant


def test_get_session_history_nonexistent():
    """Test GET /chat/sessions/{session_id} for non-existent session."""
    import uuid

    response = client.get(f"/chat/sessions/{uuid.uuid4()}")

    assert response.status_code == 404


def test_submit_feedback_accept():
    """Test POST /chat/feedback with accept."""
    import uuid

    # Create session
    response1 = client.post("/chat", json={"message": "Test"})
    session_id = response1.json()["session_id"]

    # Submit feedback
    response = client.post(
        "/chat/feedback",
        json={
            "session_id": session_id,
            "idea_id": str(uuid.uuid4()),
            "feedback_type": "accept",
            "comment": "Great idea",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "updated_context_confidence" in data


def test_submit_feedback_reject():
    """Test POST /chat/feedback with reject."""
    import uuid

    response1 = client.post("/chat", json={"message": "Test"})
    session_id = response1.json()["session_id"]

    response = client.post(
        "/chat/feedback",
        json={
            "session_id": session_id,
            "idea_id": str(uuid.uuid4()),
            "feedback_type": "reject",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_submit_feedback_flag():
    """Test POST /chat/feedback with flag."""
    import uuid

    response1 = client.post("/chat", json={"message": "Test"})
    session_id = response1.json()["session_id"]

    response = client.post(
        "/chat/feedback",
        json={
            "session_id": session_id,
            "idea_id": str(uuid.uuid4()),
            "feedback_type": "flag",
            "comment": "Review later",
        },
    )

    assert response.status_code == 200


def test_submit_feedback_invalid_session():
    """Test POST /chat/feedback with non-existent session."""
    import uuid

    response = client.post(
        "/chat/feedback",
        json={
            "session_id": str(uuid.uuid4()),
            "idea_id": str(uuid.uuid4()),
            "feedback_type": "accept",
        },
    )

    assert response.status_code == 400


def test_close_session():
    """Test DELETE /chat/sessions/{session_id}."""
    # Create session
    response1 = client.post("/chat/sessions")
    session_id = response1.json()["id"]

    # Close session
    response = client.delete(f"/chat/sessions/{session_id}")

    assert response.status_code == 204

    # Verify session is inactive
    history = client.get(f"/chat/sessions/{session_id}")
    assert history.json()["session"]["is_active"] is False


def test_close_nonexistent_session():
    """Test DELETE /chat/sessions/{session_id} for non-existent session."""
    import uuid

    response = client.delete(f"/chat/sessions/{uuid.uuid4()}")

    assert response.status_code == 404


def test_health_check():
    """Test GET /healthz."""
    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["agent"] == "aletheia"


def test_full_conversation_flow():
    """Test complete conversation flow."""
    # 1. Create session
    session_response = client.post("/chat/sessions")
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    # 2. Send multiple messages
    messages = [
        "Tell me about tokenized deposits",
        "How do they relate to stablecoins?",
        "What are the liquidity considerations?",
    ]

    for message in messages:
        response = client.post(
            "/chat", json={"session_id": session_id, "message": message}
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    # 3. Get session history
    history = client.get(f"/chat/sessions/{session_id}")
    assert history.status_code == 200
    assert len(history.json()["messages"]) == 6  # 3 user + 3 assistant

    # 4. Close session
    close_response = client.delete(f"/chat/sessions/{session_id}")
    assert close_response.status_code == 204


def test_api_documentation_available():
    """Test that API documentation endpoints are available."""
    # OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200

    # Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200
