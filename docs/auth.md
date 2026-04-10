# Authentication

FlaskIQ uses **JWT (JSON Web Tokens)** for API authentication and **Flask-WTF CSRF** for browser form protection.

## JWT Flow

```
1. POST /api/v1/auth/register  → create account
2. POST /api/v1/auth/login     → receive JWT token
3. Include token in requests:  Authorization: Bearer <token>
```

The token encodes:
```json
{
  "user": { "id": 1, "username": "johndoe", "email": "john@..." },
  "exp": "<UTC timestamp>"
}
```

Tokens expire after `JWT_EXPIRY_MINUTES` (default: 60 minutes).

## Protecting an Endpoint

Use the `@Middleware.token_required` decorator:

```python
from flask_restful import Resource
from utils.middleware import Middleware

class MyResource(Resource):
    @Middleware.token_required
    def post(self, current_user):
        # current_user = {"id": 1, "username": "johndoe", "email": "..."}
        return {"success": True, "data": {"user": current_user}}
```

The decorator:
1. Reads `Authorization: Bearer <token>` from request headers
2. Decodes and validates the JWT
3. Injects `current_user` dict into the function
4. Returns `401` if the token is missing, expired, or invalid

## Role-Based Access

`Middleware.role_required(allowed_roles)` can be stacked on top of `token_required`:

```python
@Middleware.token_required
@Middleware.role_required(["admin"])
def delete(self, current_user, page_id):
    ...
```

The `User` model must include a `role` field for this to work.

## CSRF Protection

Browser form routes (login, register) are CSRF-protected via `Flask-WTF`.  
The `api_v1_bp` blueprint is **exempt** from CSRF because API clients authenticate via Bearer JWT.

## Environment Variables

| Variable              | Description                         | Default   |
|-----------------------|-------------------------------------|-----------|
| `JWT_KEY`             | Secret used to sign tokens          | (required)|
| `JWT_EXPIRY_MINUTES`  | Token lifetime in minutes           | `60`      |
| `SECRET_KEY`          | Flask secret key (used for CSRF)    | (required)|
