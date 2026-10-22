# Task Manager API

A simple personal Task Manager REST API. Users can create a task (title plus optional description), list all tasks, mark a task complete, and delete a task. Single user, no authentication, in-memory storage (data is lost on restart).

Design docs:
- `docs/user-stories.md`: user stories and acceptance criteria
- `docs/architecture.md`: components, data model, endpoint definitions

## Tech Stack

- Python
- Flask
- pytest (testing)
- In-memory storage (no database)

## Commands

- Install dependencies: `pip install -r requirements.txt`
- Run tests: `pytest tests/ -v`

## Architecture

Layers, with dependencies pointing downward only: routes -> service -> repository -> model. See `docs/architecture.md` for details.

- Routes handle HTTP only (parse request, pick status code, return JSON).
- The service holds business rules and has no Flask imports.
- The repository owns storage and ID generation.
- The app is built by a `create_app()` factory, with no module-level global state.

## Code Style

- Use docstrings on all modules, classes, and functions.
- Use type hints on all function signatures.
- Use proper HTTP status codes: 201 for create, 200 for read/update, 204 for delete, 400 for validation errors, 404 for missing resources, 405 for wrong methods.

## Conventions

- All API responses use JSON, including errors.
- Errors use one consistent structure: `{"error": "<message>"}`.
- Error responses never expose stack traces or internal details.
- Raise domain exceptions (`ValidationError`, `TaskNotFoundError`) in the service and repository. Only the central error handlers turn them into HTTP responses.
