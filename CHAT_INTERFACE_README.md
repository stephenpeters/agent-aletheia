# Aletheia Chat Interface v1.0

**Status**: Implemented (MVP)
**Version**: 0.2.0
**Date**: 28 Oct 2025

---

## Overview

Aletheia now includes a conversational interface that enables interactive ideation and reflection. The chat interface maintains session-based conversations with context tracking, topic extraction, and integration with the memory system.

### Key Features

✅ **Session-based conversations** with 30-day memory
✅ **Topic extraction and weighting** for context building
✅ **Feedback system** (accept/reject/flag ideas)
✅ **Context confidence scoring**
✅ **Configurable context window** (default 10 messages)
✅ **Performance tracking** (latency metrics)
✅ **Graceful fallback** when Mnemosyne unavailable

---

## API Endpoints

### POST /chat

Send a message to Aletheia and get a response.

**Request:**
```json
{
  "session_id": "uuid or null",
  "message": "Find me ideas about tokenized deposits",
  "context_window": 10,
  "topics": ["liquidity", "stablecoins"],
  "include_ideas": true
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "message_id": "uuid",
  "content": "I understand you're interested in...",
  "ideas": [
    {
      "idea_id": "uuid",
      "title": "Tokenized deposit frameworks",
      "summary": "Brief summary...",
      "relevance_score": 0.87,
      "source": "URL or RSS"
    }
  ],
  "topics_discussed": ["tokenized deposits", "liquidity"],
  "context_confidence": 0.9,
  "mnemosyne_available": true,
  "latency_ms": 342
}
```

---

### POST /chat/sessions

Create a new chat session.

**Request:**
```json
{
  "user_id": "optional_user_id"
}
```

**Response:**
```json
{
  "id": "uuid",
  "user_id": "optional_user_id",
  "created_at": "2025-10-28T00:00:00Z",
  "topics": [],
  "topic_weights": {},
  "message_count": 0,
  "context_confidence": 0.8,
  "is_active": true
}
```

---

### GET /chat/sessions

List all chat sessions.

**Query Parameters:**
- `user_id` (optional): Filter by user
- `active_only` (optional): Only return active sessions

**Response:**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "title": "Discussion about liquidity",
      "created_at": "2025-10-28T00:00:00Z",
      "last_message_at": "2025-10-28T01:00:00Z",
      "topics": ["liquidity", "stablecoins"],
      "message_count": 15,
      "ideas_generated": 5,
      "ideas_accepted": 3,
      "is_active": true
    }
  ],
  "total": 10,
  "active_count": 3
}
```

---

### GET /chat/sessions/{session_id}

Get full history of a chat session.

**Response:**
```json
{
  "session": {
    "id": "uuid",
    "topics": ["liquidity", "tokenized deposits"],
    "message_count": 15,
    "ideas_generated": 5
  },
  "messages": [
    {
      "id": "uuid",
      "session_id": "uuid",
      "role": "user",
      "content": "Tell me about tokenized deposits",
      "timestamp": "2025-10-28T00:00:00Z",
      "idea_refs": []
    },
    {
      "id": "uuid",
      "session_id": "uuid",
      "role": "assistant",
      "content": "Tokenized deposits are...",
      "timestamp": "2025-10-28T00:00:05Z",
      "idea_refs": ["uuid1", "uuid2"],
      "context_confidence": 0.92
    }
  ],
  "ideas_referenced": ["uuid1", "uuid2", "uuid3"]
}
```

---

### POST /chat/feedback

Submit feedback on an idea (accept/reject/flag).

**Request:**
```json
{
  "session_id": "uuid",
  "idea_id": "uuid",
  "feedback_type": "accept",
  "comment": "This is exactly what I was looking for",
  "timestamp": "2025-10-28T00:00:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Feedback recorded successfully",
  "updated_context_confidence": 0.93
}
```

---

### DELETE /chat/sessions/{session_id}

Close (deactivate) a chat session.

**Response:** 204 No Content

---

## Architecture

### ChatService

The core service managing all chat operations:

```python
class ChatService:
    """Service for managing chat sessions and conversations."""

    async def create_session(user_id: Optional[str]) -> ChatSession
    async def get_session(session_id: UUID) -> Optional[ChatSession]
    async def list_sessions(...) -> SessionListResponse
    async def get_session_history(session_id: UUID) -> SessionHistoryResponse
    async def send_message(request: ChatRequest) -> ChatResponse
    async def submit_feedback(feedback: FeedbackRequest) -> FeedbackResponse
```

### Storage

**Current (MVP):**
- In-memory dictionaries for sessions and messages
- No persistence across restarts

**Planned:**
- PostgreSQL for session and message persistence
- Redis for session cache
- Integration with Mnemosyne for long-term memory

### Context Management

**Topic Extraction:**
- Simple keyword matching (MVP)
- Extracts topics from user messages
- Maintains topic weights per session
- TODO: NLP-based topic extraction

**Context Window:**
- Configurable number of previous messages (default: 10)
- Includes recent message history in prompts
- Maintains conversation continuity

**Context Confidence:**
- Scored 0.0 to 1.0
- Higher when Mnemosyne is available
- Adjusts based on feedback and session age
- Default: 0.8

---

## Integration Points

### Mnemosyne Query Interface

When Mnemosyne is available, the chat service:
1. Queries relevant context using `QueryRequest`
2. Retrieves historical summaries by topic
3. Updates context confidence based on retrieval success
4. Falls back to cached context if unavailable

**Placeholder in MVP:**
```python
# TODO: Initialize Mnemosyne client
self.mnemosyne_client = None
```

### Claude API

Response generation uses Claude for natural conversation:

**Placeholder in MVP:**
```python
# TODO: Call Claude API
# For MVP, returns simple response
```

### Idea Discovery

Chat can trigger idea searches based on conversation topics:

**Placeholder in MVP:**
```python
# TODO: Integrate with idea discovery
# For MVP, returns empty list
```

---

## Usage Examples

### Starting a Conversation

```bash
# Create a new session
curl -X POST http://localhost:8001/chat/sessions

# Send first message
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to explore ideas about tokenized deposits",
    "include_ideas": true
  }'
```

### Continuing a Conversation

```bash
# Send message to existing session
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-uuid",
    "message": "Tell me more about the liquidity aspects"
  }'
```

### Providing Feedback

```bash
# Accept an idea
curl -X POST http://localhost:8001/chat/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-uuid",
    "idea_id": "idea-uuid",
    "feedback_type": "accept",
    "comment": "This is helpful"
  }'
```

### Viewing History

```bash
# Get full session history
curl -X GET http://localhost:8001/chat/sessions/{session_id}
```

---

## Performance Targets (FRD)

Based on Aletheia Chat Interface v1.0 FRD:

| Metric | Target | Current (MVP) |
|--------|--------|---------------|
| Response latency | < 500ms | Tracked, not optimized |
| Context coherence | ≥ 95% over 15-turn conversation | Not measured |
| Refresh completion | < 2 min | Not implemented |
| Offline resilience | 72h | In-memory only |

---

## TODO / Next Steps

### Immediate (Week 3-4):
- [ ] Integrate Claude API for response generation
- [ ] Add database persistence (PostgreSQL)
- [ ] Connect to Mnemosyne query interface
- [ ] Implement actual idea search integration
- [ ] Add unit tests for ChatService
- [ ] Add integration tests for chat routes

### v1.1 Enhancements:
- [ ] WebSocket support for streaming responses
- [ ] Conversation summaries (ConversationSummary model)
- [ ] NLP-based topic extraction
- [ ] Session search and filtering
- [ ] Export conversation history

### v1.2 Advanced Features:
- [ ] Multi-user support with authentication
- [ ] Conversation branching
- [ ] Idea bookmarking within chat
- [ ] Voice input/output (speech-to-text/text-to-speech)

### v2.0 Multimodal:
- [ ] Image upload and analysis
- [ ] Visual-text embedding fusion
- [ ] Cross-modal recall
- [ ] Image-based idea generation

---

## Testing

### Manual Testing

Start Aletheia locally:
```bash
cd agent-aletheia
uvicorn main:app --reload --port 8001
```

Access interactive API docs:
```
http://localhost:8001/docs
```

### Automated Testing

```bash
# Run unit tests
pytest tests/unit/test_chat_service.py

# Run integration tests
pytest tests/integration/test_chat_routes.py

# Test 15-turn conversation (context coherence)
pytest tests/integration/test_conversation_coherence.py
```

---

## Troubleshooting

### Session not found
- Sessions are stored in-memory for MVP
- Restarting the server clears all sessions
- Check session_id is a valid UUID

### Low context confidence
- Mnemosyne may be unavailable
- Check Mnemosyne service status
- System operates in fallback mode with cached context

### Slow response times
- Current MVP uses placeholder response generation
- Claude API integration will improve quality
- Consider implementing response caching

---

## References

- **FRD**: [aletheia_chat_frd.md](aletheia_chat_frd.md)
- **PRD Update**: [agent-alethia-update-prd.md](agent-alethia-update-prd.md)
- **Memory Architecture**: [MEMORY_SYSTEM_ARCHITECTURE.md](../MEMORY_SYSTEM_ARCHITECTURE.md)
- **Chat Models**: [agent-sdk/agent_sdk/models/chat.py](../agent-sdk/agent_sdk/models/chat.py)

---

## Change Log

**v0.2.0 - 28 Oct 2025**
- Initial chat interface implementation
- Session management and message history
- Topic extraction and context tracking
- Feedback system for ideas
- 6 REST API endpoints
- In-memory storage for MVP
- Structured logging throughout

**Future:**
- v0.3.0: Database persistence, Claude integration
- v0.4.0: Mnemosyne integration, idea search
- v1.0.0: Production-ready with all FRD v1.0 features
- v1.1.0: WebSocket streaming, conversation summaries
- v2.0.0: Multimodal capabilities (images)
