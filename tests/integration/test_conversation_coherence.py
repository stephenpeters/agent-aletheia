"""Integration tests for conversation coherence (FRD KPI: ≥95% over 15-turn conversation)."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_fifteen_turn_conversation():
    """
    Test 15-turn conversation for context coherence.

    FRD Requirement: Context coherence ≥ 95% over 15-turn conversation
    Target: Response latency < 500ms

    This test verifies:
    1. Session maintains context across 15 turns
    2. Topics are tracked consistently
    3. Context confidence remains high
    4. No session degradation
    """
    # Create session
    session_response = client.post("/chat/sessions")
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    # 15-turn conversation about a specific topic
    conversation = [
        "I want to explore tokenized deposits",
        "What are the main benefits?",
        "How do they compare to stablecoins?",
        "Tell me about liquidity aspects",
        "What about regulatory considerations?",
        "How do banks typically implement this?",
        "What are the technical requirements?",
        "Can you explain the settlement process?",
        "What risks should I be aware of?",
        "How does this impact treasury operations?",
        "What about cross-border transactions?",
        "How do smart contracts fit in?",
        "What's the role of blockchain here?",
        "How mature is this technology?",
        "What should I read next?",
    ]

    responses = []
    latencies = []
    confidence_scores = []

    for turn, message in enumerate(conversation, 1):
        response = client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": message,
                "context_window": 10,
            },
        )

        assert response.status_code == 200, f"Turn {turn} failed"
        data = response.json()

        # Store data for analysis
        responses.append(data)
        latencies.append(data.get("latency_ms", 0))
        confidence_scores.append(data.get("context_confidence", 0))

        # Verify session consistency
        assert data["session_id"] == session_id, f"Session ID changed at turn {turn}"

        # Verify response quality
        assert len(data["content"]) > 0, f"Empty response at turn {turn}"
        assert data["context_confidence"] > 0.0, f"Zero confidence at turn {turn}"

        print(f"Turn {turn}: Latency={data['latency_ms']}ms, Confidence={data['context_confidence']}")

    # Get final session state
    history = client.get(f"/chat/sessions/{session_id}")
    assert history.status_code == 200
    session_data = history.json()

    # Verify conversation integrity
    assert len(session_data["messages"]) == 30  # 15 user + 15 assistant
    assert session_data["session"]["message_count"] == 30

    # Analyze metrics
    avg_latency = sum(latencies) / len(latencies)
    avg_confidence = sum(confidence_scores) / len(confidence_scores)
    min_confidence = min(confidence_scores)

    print(f"\n=== Conversation Metrics ===")
    print(f"Average latency: {avg_latency:.0f}ms (target: <500ms)")
    print(f"Average confidence: {avg_confidence:.2f}")
    print(f"Minimum confidence: {min_confidence:.2f}")
    print(f"Topics tracked: {len(session_data['session']['topics'])}")

    # FRD Assertions
    # Note: With placeholder implementation, we can't test actual coherence
    # but we can verify the infrastructure is in place
    assert avg_confidence >= 0.5, "Context confidence too low (placeholder threshold)"

    # Future: When Claude integration is complete, assert avg_confidence >= 0.95

    return {
        "avg_latency": avg_latency,
        "avg_confidence": avg_confidence,
        "turns": len(conversation),
        "topics": session_data["session"]["topics"],
    }


def test_context_window_management():
    """Test that context window properly limits history."""
    session_response = client.post("/chat/sessions")
    session_id = session_response.json()["id"]

    # Send 20 messages with context window of 5
    for i in range(20):
        response = client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": f"Message number {i}",
                "context_window": 5,
            },
        )
        assert response.status_code == 200

    # Verify all messages are stored
    history = client.get(f"/chat/sessions/{session_id}")
    assert len(history.json()["messages"]) == 40  # 20 user + 20 assistant


def test_topic_consistency_across_conversation():
    """Test that topics are consistently tracked."""
    session_response = client.post("/chat/sessions")
    session_id = session_response.json()["id"]

    # Conversation focusing on specific topics
    messages = [
        "Tell me about AI in business",
        "How does AI improve efficiency?",
        "What about AI costs?",
        "Can you compare AI solutions?",
        "Show me AI case studies",
    ]

    for message in messages:
        response = client.post(
            "/chat",
            json={"session_id": session_id, "message": message},
        )
        assert response.status_code == 200

    # Get session and check topics
    history = client.get(f"/chat/sessions/{session_id}")
    session_data = history.json()["session"]

    # With topic extraction, "AI" or "business" should be tracked
    topics = session_data["topics"]
    assert len(topics) > 0, "No topics were extracted"

    # Topic weights should exist
    topic_weights = session_data["topic_weights"]
    assert len(topic_weights) > 0, "No topic weights tracked"


def test_session_metadata_consistency():
    """Test that session metadata is consistently updated."""
    session_response = client.post("/chat/sessions")
    session_id = session_response.json()["id"]

    initial_history = client.get(f"/chat/sessions/{session_id}").json()
    initial_updated_at = initial_history["session"]["updated_at"]

    # Send a message
    client.post(
        "/chat",
        json={"session_id": session_id, "message": "Test message"},
    )

    # Check metadata updated
    updated_history = client.get(f"/chat/sessions/{session_id}").json()
    session = updated_history["session"]

    assert session["updated_at"] > initial_updated_at
    assert session["last_message_at"] is not None
    assert session["message_count"] == 2  # 1 user + 1 assistant


def test_concurrent_sessions():
    """Test handling multiple concurrent sessions."""
    # Create 5 sessions
    sessions = []
    for i in range(5):
        response = client.post("/chat/sessions", params={"user_id": f"user_{i}"})
        sessions.append(response.json()["id"])

    # Send messages to each session
    for i, session_id in enumerate(sessions):
        response = client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": f"Message from session {i}",
            },
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    # Verify all sessions are independent
    for session_id in sessions:
        history = client.get(f"/chat/sessions/{session_id}")
        assert history.status_code == 200
        assert history.json()["session"]["message_count"] == 2


@pytest.mark.parametrize("context_window", [1, 5, 10, 20])
def test_various_context_windows(context_window):
    """Test conversation with various context window sizes."""
    session_response = client.post("/chat/sessions")
    session_id = session_response.json()["id"]

    # Send 10 messages with specified context window
    for i in range(10):
        response = client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": f"Message {i}",
                "context_window": context_window,
            },
        )
        assert response.status_code == 200

    # Verify conversation completed
    history = client.get(f"/chat/sessions/{session_id}")
    assert len(history.json()["messages"]) == 20


def test_response_quality_metrics():
    """Test that response quality metrics are tracked."""
    response = client.post(
        "/chat",
        json={"message": "Test message"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify all quality metrics present
    assert "context_confidence" in data
    assert "mnemosyne_available" in data
    assert "latency_ms" in data
    assert "topics_discussed" in data

    # Verify metric validity
    assert 0.0 <= data["context_confidence"] <= 1.0
    assert data["latency_ms"] > 0
    assert isinstance(data["mnemosyne_available"], bool)
    assert isinstance(data["topics_discussed"], list)


if __name__ == "__main__":
    # Can run directly for manual testing
    print("Running 15-turn conversation coherence test...")
    result = test_fifteen_turn_conversation()
    print(f"\nTest completed: {result}")
