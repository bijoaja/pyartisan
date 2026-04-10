# FlaskIQ

**FlaskIQ** is a production-ready Flask project template that enforces a clean, layered architecture out of the box.

## Tech Stack

| Layer         | Technology                                      |
|---------------|-------------------------------------------------|
| Framework     | Flask 3.1, Flask-RESTful                        |
| Database      | SQLAlchemy, Flask-Migrate (SQLite / MySQL)      |
| Auth          | PyJWT, Flask-WTF (CSRF)                         |
| Rate limiting | Flask-Limiter (tenant-aware)                    |
| AI / LLM      | Ollama (local) or OpenAI via LangChain          |
| Frontend      | Tailwind CSS (Play CDN), Bootstrap Icons        |
| API docs      | Swagger UI via flask-swagger-ui                 |
| Deployment    | Docker (dev + prod), Gunicorn, Makefile         |

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Start the dev server (Docker)
make dev

# 3. Run database migrations
make db-setup

# 4. Open the app
open http://localhost:8080
open http://localhost:8080/api/v1/docs   # Swagger UI
```

## Key URLs

| URL                      | Description                        |
|--------------------------|------------------------------------|
| `/`                      | Landing page                       |
| `/cms`                   | CMS pages list                     |
| `/login`                 | Login page                         |
| `/register`              | Registration page                  |
| `/api/v1/docs`           | Swagger UI (interactive API docs)  |
| `/api/v1/auth/register`  | API: register user                 |
| `/api/v1/auth/login`     | API: login and receive JWT         |
| `/api/v1/chatbot`        | API: streaming AI chatbot          |
| `/api/v1/cms`            | API: CMS CRUD                      |

## Further Reading

- [Architecture](architecture.md)
- [API Reference](api.md)
- [Authentication](auth.md)
- [AI Agent / Chatbot](agent.md)
- [Docker & Makefile](docker.md)
