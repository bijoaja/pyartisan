# API Reference

Base URL: `http://localhost:8080`  
Interactive docs: `GET /api/v1/docs` (Swagger UI)

All JSON responses follow this envelope:

```json
{
  "success": true,
  "data": { ... },
  "message": "Human-readable message"
}
```

---

## General

### `GET /api/v1/`
Welcome message. No auth required.

```bash
curl http://localhost:8080/api/v1/
```

---

## Auth

### `POST /api/v1/auth/register`
Register a new user account.

**Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "secret123"
}
```

**Response `201`:**
```json
{
  "success": true,
  "data": { "id": 1, "username": "johndoe", "email": "john@example.com" },
  "message": "User registered successfully."
}
```

**Error `409`:** Email or username already registered.

---

### `POST /api/v1/auth/login`
Authenticate and receive a JWT token.

**Body:**
```json
{ "email": "john@example.com", "password": "secret123" }
```

**Response `200`:**
```json
{
  "success": true,
  "data": { "token": "eyJ..." },
  "message": "Login successful."
}
```

**Error `401`:** Invalid credentials.

---

## Chatbot

### `POST /api/v1/chatbot`
Stream an AI response. Returns `text/plain` chunked response.

**Body:**
```json
{ "message": "What is FlaskIQ?" }
```

**Response:** Streaming plain text (use `--no-buffer` with curl):

```bash
curl -X POST http://localhost:8080/api/v1/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message": "What is FlaskIQ?"}' --no-buffer
```

---

## CMS

### `GET /api/v1/cms`
List all pages (includes unpublished). No auth required.

```bash
curl http://localhost:8080/api/v1/cms
```

---

### `POST /api/v1/cms` 🔒
Create a page. Requires `Authorization: Bearer <token>`.

**Body:**
```json
{
  "title": "Hello World",
  "slug": "hello-world",
  "content": "<p>My first page.</p>",
  "is_published": true
}
```

---

### `GET /api/v1/cms/<id>`
Get a page by numeric ID.

---

### `PUT /api/v1/cms/<id>` 🔒
Update a page. Partial updates are supported.

```json
{ "is_published": false }
```

---

### `DELETE /api/v1/cms/<id>` 🔒
Delete a page permanently.

---

## Full authenticated example

```bash
# Register
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@test.com","password":"secret123"}'

# Login — capture token
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"secret123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# Create page
curl -X POST http://localhost:8080/api/v1/cms \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Hello","slug":"hello","content":"<p>World</p>","is_published":true}'

# Read page in browser
open http://localhost:8080/cms/page/hello
```
