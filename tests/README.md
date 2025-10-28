# Aletheia Test Suite

Comprehensive test scaffolding to ensure the Aletheia interface stays consistent across development.

---

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   └── test_chat_service.py    # ChatService tests (17 tests)
├── integration/             # Integration tests for API endpoints
│   ├── test_chat_routes.py     # Chat API endpoint tests (22 tests)
│   └── test_conversation_coherence.py  # FRD KPI tests (8 tests)
└── README.md               # This file
```

---

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit
```

### Integration Tests Only
```bash
pytest tests/integration
```

### Specific Test File
```bash
pytest tests/unit/test_chat_service.py
```

### Specific Test Function
```bash
pytest tests/integration/test_conversation_coherence.py::test_fifteen_turn_conversation
```

### With Coverage Report
```bash
pytest --cov=agent_aletheia --cov-report=html
```

### Verbose Output
```bash
pytest -v
```

---

## Test Categories

### Unit Tests (`tests/unit/test_chat_service.py`)

Tests for ChatService business logic without HTTP layer:

- **Session Management**: create, retrieve, list sessions
- **Message Handling**: send messages, maintain history
- **Topic Extraction**: identify and track conversation topics
- **Context Window**: manage conversation history limits
- **Feedback System**: accept/reject/flag ideas
- **Context Confidence**: track confidence scores
- **Latency Tracking**: measure response times

**17 tests total**

### Integration Tests (`tests/integration/test_chat_routes.py`)

Tests for HTTP API endpoints and request/response handling:

- **POST /chat**: Send messages, create sessions
- **POST /chat/sessions**: Create new sessions
- **GET /chat/sessions**: List sessions with filtering
- **GET /chat/sessions/{id}**: Retrieve session history
- **POST /chat/feedback**: Submit feedback
- **DELETE /chat/sessions/{id}**: Close sessions
- **Full Conversation Flow**: End-to-end conversation test

**22 tests total**

### Conversation Coherence Tests (`tests/integration/test_conversation_coherence.py`)

Tests for FRD KPI requirements and conversation quality:

- **15-Turn Conversation**: FRD requirement (≥95% coherence)
- **Context Window Management**: Verify history limits
- **Topic Consistency**: Track topics across conversation
- **Session Metadata**: Ensure consistent updates
- **Concurrent Sessions**: Handle multiple conversations
- **Various Context Windows**: Test with different window sizes
- **Response Quality Metrics**: Verify all metrics present

**8 tests total**

**Key Test:**
```python
def test_fifteen_turn_conversation():
    """
    FRD Requirement: Context coherence ≥ 95% over 15-turn conversation
    Target: Response latency < 500ms
    """
```

---

## CI/CD Integration

Tests run automatically on GitHub Actions for every push and pull request.

### Workflows (`.github/workflows/test.yml`)

**Jobs:**

1. **Lint Job**
   - Runs ruff for linting
   - Runs black for code formatting

2. **Test Job**
   - Runs on Python 3.11 and 3.12
   - Executes all unit and integration tests
   - Generates coverage reports
   - Uploads coverage to Codecov

3. **Interface Contract Job**
   - Verifies API endpoints exist
   - Tests chat interface consistency
   - Runs 15-turn conversation test

---

## FRD KPI Testing

Based on [aletheia_chat_frd.md](../aletheia_chat_frd.md):

| KPI | Target | Test |
|-----|--------|------|
| Response latency | < 500ms | `test_latency_tracking` |
| Context coherence | ≥ 95% over 15 turns | `test_fifteen_turn_conversation` |
| Refresh completion | < 2 min | Not implemented (requires daemon) |
| Offline resilience | 72h | Not implemented (requires persistence) |

---

## Test Fixtures

All tests use pytest fixtures for consistent test data:

```python
@pytest.fixture
def chat_service():
    """Create a ChatService instance for testing."""
    return ChatService()
```

Integration tests use FastAPI TestClient:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
```

---

## Assertions and Validation

### Session Consistency
```python
assert response.json()["session_id"] == session_id
assert session.is_active is True
assert session.message_count > 0
```

### Response Quality
```python
assert len(response["content"]) > 0
assert 0.0 <= response["context_confidence"] <= 1.0
assert response["latency_ms"] > 0
```

### API Contracts
```python
assert response.status_code == 200
assert "session_id" in data
assert "message_id" in data
assert "content" in data
```

---

## Mocking and Placeholders

Currently, certain components use placeholders:

### Claude API
```python
# TODO: Call Claude API
# For MVP, return a simple response
response = f"I understand you're interested in..."
```

**Tests work with placeholder** - will need updates when Claude integration is complete.

### Mnemosyne Integration
```python
# TODO: Query Mnemosyne
self.mnemosyne_client = None
```

**Tests verify fallback behavior** - will need additional tests when Mnemosyne is integrated.

---

## Adding New Tests

### Unit Test Template
```python
@pytest.mark.asyncio
async def test_new_feature(chat_service):
    """Test description."""
    # Arrange
    session = await chat_service.create_session()

    # Act
    result = await chat_service.some_method(session.id)

    # Assert
    assert result is not None
    assert result.some_property == expected_value
```

### Integration Test Template
```python
def test_new_endpoint():
    """Test description."""
    response = client.post(
        "/chat/new-endpoint",
        json={"param": "value"},
    )

    assert response.status_code == 200
    assert "expected_field" in response.json()
```

---

## Coverage Requirements

Target: **≥ 80% code coverage**

Current coverage areas:
- ✅ ChatService methods
- ✅ Chat API routes
- ✅ Request/response validation
- ✅ Error handling
- ⏳ Mnemosyne integration (placeholder)
- ⏳ Claude API integration (placeholder)

View coverage report:
```bash
pytest --cov=agent_aletheia --cov-report=html
open htmlcov/index.html
```

---

## Continuous Testing

### Pre-commit Hooks (Recommended)
```bash
# Install pre-commit
pip install pre-commit

# Set up git hooks
pre-commit install

# Manually run
pre-commit run --all-files
```

### Watch Mode (Development)
```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw -- tests/
```

---

## Known Limitations

### MVP Placeholders
1. **Claude API**: Response generation uses placeholder text
2. **Mnemosyne**: Context queries return mock data
3. **Database**: Sessions stored in-memory only
4. **Embeddings**: No actual embedding generation

### Future Test Needs
1. **Performance Tests**: Load testing with concurrent users
2. **Security Tests**: Input validation, injection attacks
3. **Database Tests**: Persistence, transactions, migrations
4. **Mnemosyne Integration**: Context retrieval, confidence scoring
5. **Claude Integration**: Response quality, coherence measurement

---

## Debugging Tests

### Run Single Test with Output
```bash
pytest tests/unit/test_chat_service.py::test_create_session -v -s
```

### Debug with pdb
```bash
pytest --pdb tests/unit/test_chat_service.py
```

### Show Print Statements
```bash
pytest -v -s
```

### Show Fixture Setup
```bash
pytest --setup-show
```

---

## Test Data

Tests use realistic but fake data:

- **Session IDs**: Generated UUIDs
- **User IDs**: `"test_user_123"`, `"user_1"`, etc.
- **Messages**: Contextual test messages about tokenized deposits, AI, liquidity
- **Topics**: Extracted from messages using keyword matching

---

## Maintenance

### Update Tests When:
1. API contract changes (new endpoints, request/response models)
2. Business logic changes (scoring algorithms, topic extraction)
3. FRD KPIs are updated (new targets, metrics)
4. Claude/Mnemosyne integrations are implemented
5. Database schema changes

### Test Review Checklist:
- [ ] All new features have unit tests
- [ ] All new endpoints have integration tests
- [ ] Coverage remains ≥ 80%
- [ ] CI/CD pipeline passes
- [ ] FRD KPIs are still tested
- [ ] Documentation is updated

---

## References

- **FRD**: [aletheia_chat_frd.md](../aletheia_chat_frd.md)
- **API Docs**: [CHAT_INTERFACE_README.md](../CHAT_INTERFACE_README.md)
- **Chat Service**: [agent_aletheia/services/chat.py](../agent_aletheia/services/chat.py)
- **Chat Routes**: [agent_aletheia/routes/chat.py](../agent_aletheia/routes/chat.py)
- **pytest**: https://docs.pytest.org/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

**Total Tests**: 47 tests across unit, integration, and coherence categories
**Last Updated**: 28 Oct 2025
**Status**: ✅ All tests passing with MVP implementation
