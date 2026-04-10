# Architecture

FlaskIQ uses a strict four-layer architecture. Each layer has a single responsibility and may only call the layer directly below it.

```
HTTP Request
     │
     ▼
┌─────────────┐
│   Routes    │  URL mapping — no logic, just wires URL to controller
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Controller  │  Request parsing + response formatting — no business logic
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Service   │  Business logic — calls repository, never touches db.session
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Repository  │  Data access — the ONLY layer that calls db.session
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Model    │  SQLAlchemy ORM model, to_dict() serialisation
└─────────────┘
```

## Layer Rules

### Routes (`app/routes/`)
- Map URL patterns to controller methods using Flask `Blueprint`
- Never import services or models directly
- No conditional logic

### Controllers (`app/controller/`)
- Parse `request.get_json()` / `request.args`
- Validate that required fields are present (structural validation only)
- Call exactly one service method
- Return `Response().success()` or `Response().invalid()`
- Never call `db.session` or model queries

### Services (`app/service/`)
- Contain all business logic
- Call repository methods for data access
- Raise `ValueError` for domain errors (not HTTP errors)
- Can import and call other services when needed

### Repository (`app/repository/`)
- All `db.session` operations live here exclusively
- `BaseRepository` provides: `get_by_id`, `get_all`, `save`, `delete`
- Subclasses add domain-specific queries
- Return ORM model instances (not dicts)

### Models (`app/model/`)
- Pure SQLAlchemy model definitions
- `to_dict()` for JSON serialisation (called at the controller boundary for APIs)
- Password hashing helpers on `User`

## File Naming

All files use **snake_case** (e.g., `cms_controller.py`, `user_repository.py`).  
No dot-notation filenames — standard Python imports work everywhere.

## Agent System (`app/service/agent/`)

```
ChatbotService           ← entry point (reads AI_PROVIDER env var)
├── OllamaAgent          ← requests to local Ollama server
├── OpenAIAgent          ← LangChain + openai SDK streaming
└── tools/
    └── RAGTool          ← loads README.md as system prompt (extensible)
```

Adding a new LLM provider requires only:
1. Create `app/service/agent/<provider>/<provider>_agent.py` implementing `BaseAgent`
2. Add an `elif provider == "<provider>"` branch in `ChatbotService.get_generator()`
3. Set `AI_PROVIDER=<provider>` in `.env`
