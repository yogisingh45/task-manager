# Task Manager API

A small personal Task Manager REST API built with Python and Flask. Create tasks, list them, mark them complete and delete them. It is a single-user service with no authentication, and tasks are kept **in memory**, so they are lost when the server restarts.

## Features

- Create a task with a title and an optional description
- List all tasks in creation order
- Mark a task complete (idempotent, one-way)
- Delete a task
- IDs are auto-generated and never reused, even after deletion
- JSON everywhere, with one consistent error format: `{"error": "<message>"}`
- Error responses never expose stack traces or internals
- Layered design (routes → service → repository → model) and an app factory, so a database-backed repository could replace the in-memory one without touching routes or service
- Docker and docker-compose files, plus an AWS deployment guide

## Requirements

- Python 3.12 (the Docker image uses 3.12; other recent 3.x versions should work)
- Docker (optional)

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

flask --app app run          # http://127.0.0.1:5000
# or
python app.py
```

With Docker:

```bash
docker compose up --build    # http://localhost:8000
docker compose down
```

Try it:

```bash
curl -i -X POST localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title":"Buy milk"}'
curl -i localhost:8000/tasks
```

(Use port `5000` instead of `8000` when running with `flask` or `python app.py`.)

## API documentation

All requests and responses use `application/json`. The examples below use `localhost:8000`.

### Task object

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Generated, unique, never reused |
| `title` | string | Required, non-empty after trimming, stored trimmed |
| `description` | string | Optional, defaults to `""` |
| `completed` | boolean | Defaults to `false` |

### `POST /tasks` – create a task

```bash
curl -i -X POST localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title": "Buy milk", "description": "2 litres"}'
```

```http
HTTP/1.1 201 CREATED
Content-Type: application/json

{"id": 1, "title": "Buy milk", "description": "2 litres", "completed": false}
```

`400 Bad Request` if the body is not a JSON object, `title` is missing, empty, whitespace-only or not a string, or `description` is not a string:

```json
{"error": "title is required and must not be empty"}
```

### `GET /tasks` – list all tasks

```bash
curl -i localhost:8000/tasks
```

```http
HTTP/1.1 200 OK

[{"id": 1, "title": "Buy milk", "description": "2 litres", "completed": false}]
```

Returns `[]` when there are no tasks.

### `PATCH /tasks/{id}/complete` – mark a task complete

```bash
curl -i -X PATCH localhost:8000/tasks/1/complete
```

```http
HTTP/1.1 200 OK

{"id": 1, "title": "Buy milk", "description": "2 litres", "completed": true}
```

Completing an already complete task also returns `200`. `404` if the task does not exist.

### `DELETE /tasks/{id}` – delete a task

```bash
curl -i -X DELETE localhost:8000/tasks/1
```

```http
HTTP/1.1 204 NO CONTENT
```

`404` if the task does not exist (including a repeat delete).

### Errors

Every error has the same shape:

```json
{"error": "Task not found"}
```

| Status | Cause |
|---|---|
| `400` | Validation failure or malformed JSON body |
| `404` | Unknown task ID, unknown route, or non-integer `{id}` |
| `405` | Unsupported method on an existing route |
| `500` | Unhandled error (generic message, details only in the server log) |

## Running the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

`pytest.ini` puts the project root on the import path and sets `tests/` as the test directory. Tests use Flask's test client against a fresh `create_app()`, so each test has isolated state.

## Deployment

The app ships with a `Dockerfile` (gunicorn, one worker with four threads, non-root user, health check on `GET /tasks`) and a `docker-compose.yml`.

```bash
docker build -t task-manager:latest .
```

For AWS, the recommended target is **ECS on Fargate with exactly one task**. Because storage is in memory, Lambda or multiple tasks would give users inconsistent data. See [docs/deployment-guide.md](docs/deployment-guide.md) for the reasoning, sources, step-by-step commands and environment variables.

> The Docker artifacts were reviewed but have not yet been built or run. Do a first build and smoke test before relying on them.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Port gunicorn listens on inside the container |

## Project structure

```
task-manager/
├── app.py                          # entry point: app = create_app()
├── task_manager/
│   ├── __init__.py                 # create_app() factory
│   ├── errors.py                   # domain exceptions + central error handlers
│   ├── models/task.py              # Task dataclass
│   ├── repositories/
│   │   └── task_repository.py      # in-memory storage, ID generation, lock
│   ├── services/
│   │   └── task_service.py         # business rules and validation
│   └── routes/tasks.py             # HTTP routes (Blueprint)
├── tests/test_app.py               # API tests
├── docs/
│   ├── user-stories.md             # user stories and acceptance criteria
│   ├── architecture.md             # components, data model, endpoints
│   └── deployment-guide.md         # Docker and AWS deployment
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pytest.ini
```

Dependencies point downward only: routes → service → repository → model. See [docs/architecture.md](docs/architecture.md) for details.
