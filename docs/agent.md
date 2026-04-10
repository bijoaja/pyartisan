# AI Agent / Chatbot

FlaskIQ includes a multi-provider AI chatbot with streaming responses.

## How It Works

```
POST /api/v1/chatbot  { "message": "..." }
          │
          ▼
  ChatbotService.get_generator(user_message)
          │
          ├─ reads AI_PROVIDER env var
          ├─ builds system_prompt via RAGTool (loads README.md)
          │
          ├─ AI_PROVIDER=ollama  → OllamaAgent  (local Ollama server)
          └─ AI_PROVIDER=openai  → OpenAIAgent  (OpenAI API via LangChain)
```

Response is a streaming generator — text chunks are sent to the client in real time.

## Switching Providers

Set `AI_PROVIDER` in `.env`:

```bash
# Use local Ollama (default)
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral

# Use OpenAI
AI_PROVIDER=openai
AI_KEY=sk-YOUR_OPENAI_KEY
OPENAI_MODEL=gpt-4o-mini
```

## Adding a New Provider

1. Create `app/service/agent/<provider>/<provider>_agent.py`:

```python
from app.service.agent.base_agent import BaseAgent

class MyProviderAgent(BaseAgent):
    def get_generator(self, user_message: str, system_prompt: dict):
        # call your API, return a generator that yields strings
        ...
```

2. Add a branch in `app/service/agent/chatbot_service.py`:

```python
elif provider == "myprovider":
    from app.service.agent.myprovider.myprovider_agent import MyProviderAgent
    agent = MyProviderAgent()
```

3. Set `AI_PROVIDER=myprovider` in `.env`.

## RAGTool (Knowledge Base)

`RAGTool` (`app/service/agent/tools/rag_tool.py`) reads `README.md` and injects it as the system prompt so the assistant has project context.

To extend it with a vector store:

```python
class RAGTool(BaseTool):
    def run(self, input: str) -> str:
        # Replace this with a vector-store similarity search
        results = vector_store.similarity_search(input, k=5)
        return "\n\n".join(doc.page_content for doc in results)
```

## File Structure

```
app/service/agent/
├── base_agent.py          ← BaseAgent ABC (get_generator interface)
├── chatbot_service.py     ← entry point, provider dispatch
├── ollama/
│   └── ollama_agent.py    ← streams from Ollama /api/chat
├── openai/
│   └── openai_agent.py    ← streams via LangChain + openai SDK
└── tools/
    ├── base_tool.py       ← BaseTool ABC
    └── rag_tool.py        ← loads README.md as system prompt
```
