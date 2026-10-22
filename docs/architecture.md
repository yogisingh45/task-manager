# Task Manager API – Architecture

Derived from [user-stories.md](user-stories.md) (US-1 to US-5). Python + Flask, in-memory storage, single user, no authentication.

## 1. Component Overview

The app uses three layers plus an app factory. Each layer depends only on the layer below it.

```
                 HTTP client (curl, Postman, frontend)
                                |
                                v  JSON over HTTP
+---------------------------------------------------------------+
|  Flask Application  (app factory: create_app)                 |
|                                                               |
|  +---------------------------+   +--------------------------+ |
|  | Error Handlers            |   | Routes (Blueprint)       | |
|  | 400 / 404 / 405 / 500     |<--| /tasks endpoints         | |
|  | -> {"error": "..."}       |   | parse + validate request | |
|  +---------------------------+   | serialize response       | |
|                                  +------------+-------------+ |
|                                               | calls         |
|                                               v               |
|                                  +--------------------------+ |
|                                  | TaskService              | |
|                                  | business rules:          | |
|                                  | create/list/complete/    | |
|                                  | delete; raises           | |
|                                  | ValidationError,         | |
|                                  | TaskNotFoundError        | |
|                                  +------------+-------------+ |
|                                               | calls         |
|                                               v               |
|                                  +--------------------------+ |
|                                  | TaskRepository           | |
|                                  | in-memory dict + ID      | |
|                                  | counter (+ lock)         | |
|                                  +--------------------------+ |
+---------------------------------------------------------------+
```

### Components

| Component | Responsibility | Knows about |
|---|---|---|
| **App factory** (`create_app`) | Builds the Flask app, creates the repository and service, registers the blueprint and error handlers. | All components (wiring only) |
| **Routes** (`routes/tasks.py`, Blueprint) | HTTP concerns: read JSON body, call the service, choose status codes, return JSON. | Service, exceptions |
| **TaskService** (`services/task_service.py`) | Business rules: title validation, defaults, completion. Raises domain exceptions. No Flask imports. | Repository, Task model, exceptions |
| **TaskRepository** (`repositories/task_repository.py`) | Storage: holds tasks in a dict, generates IDs, and provides add/get/list/delete. | Task model |
| **Task model** (`models/task.py`) | Dataclass defining a task and its `to_dict()` serialization. | Nothing |
| **Exceptions** (`errors.py`) | `ValidationError`, `TaskNotFoundError`. | Nothing |
| **Error handlers** (`errors.py`, registered in factory) | Map exceptions and HTTP errors to the `{"error": "<message>"}` format (US-5). | Exceptions |

### Why this split

- Routes contain no business logic, so the service can be unit-tested without HTTP.
- The repository hides the storage, so a database could replace the dict without touching routes or service.
- The app factory creates a fresh repository for each app instance, so tests get isolated state.

### Proposed layout

```
task-manager/
├── app.py                    # entry point: app = create_app()
├── task_manager/
│   ├── __init__.py           # create_app()
│   ├── errors.py             # exceptions + error handlers
│   ├── models/task.py
│   ├── repositories/task_repository.py
│   ├── services/task_service.py
│   └── routes/tasks.py
├── tests/
├── docs/
└── requirements.txt
```

## 2. Data Model

### Task

| Attribute | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | `int` | generated | auto-increment from 1 | Unique and never reused, even after deletion (US-1.7). |
| `title` | `str` | yes | none | Non-empty after trimming whitespace. Stored trimmed. |
| `description` | `str` | no | `""` | |
| `completed` | `bool` | no | `False` | Set to `True` by the complete operation. One-way. |

```python
@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    completed: bool = False
```

### Storage

- `_tasks: dict[int, Task]` maps ID to task. Python dicts keep insertion order, so listing returns creation order (US-2.4).
- `_next_id: int` is a monotonic counter that is only incremented, so IDs are never reused.
- A `threading.Lock` guards ID generation and mutations, because Flask's dev server can handle requests on multiple threads.
- State lives in the repository instance, so it is lost on restart (accepted by design).

### JSON representation

```json
{
  "id": 1,
  "title": "Buy milk",
  "description": "2 litres, semi-skimmed",
  "completed": false
}
```

## 3. API Endpoints

All requests and responses use `application/json`.

### POST /tasks – Create a task (US-1)

**Request body**

| Field | Type | Required |
|---|---|---|
| `title` | string | yes |
| `description` | string | no |

```json
{ "title": "Buy milk", "description": "2 litres" }
```

**Responses**

| Status | When | Body |
|---|---|---|
| `201 Created` | Task created | The task object |
| `400 Bad Request` | Body is not valid JSON or not an object; `title` missing, empty, whitespace-only or not a string; `description` not a string | `{"error": "..."}` |

### GET /tasks – List all tasks (US-2)

**Request:** no body.

| Status | When | Body |
|---|---|---|
| `200 OK` | Always | JSON array of task objects in creation order, `[]` if none |

### PATCH /tasks/{id}/complete – Mark a task complete (US-3)

**Request:** no body. `id` is an integer path parameter.

| Status | When | Body |
|---|---|---|
| `200 OK` | Task exists (including when it is already complete) | The updated task object with `completed: true` |
| `404 Not Found` | No task with that ID | `{"error": "Task not found"}` |

### DELETE /tasks/{id} – Delete a task (US-4)

**Request:** no body. `id` is an integer path parameter.

| Status | When | Body |
|---|---|---|
| `204 No Content` | Task existed and was deleted | none |
| `404 Not Found` | No task with that ID (including a repeat delete) | `{"error": "Task not found"}` |

### Error format (US-5)

Every error response has the same shape:

```json
{ "error": "Task not found" }
```

| Status | Cause |
|---|---|
| `400` | `ValidationError`, or malformed JSON body |
| `404` | `TaskNotFoundError`, unknown route, or non-integer `{id}` (the `<int:id>` converter does not match) |
| `405` | Unsupported method on a defined route |
| `500` | Unhandled exception. The message is generic, with no stack trace or internals. |

## 4. Component Interaction

### Request flow

```
Client -> Flask router -> Route handler -> TaskService -> TaskRepository
                                                              |
Client <- JSON response <- Route handler <- Task / exception -+
                               \-> Error handler (on exception)
```

### Create a task: `POST /tasks`

1. The route reads the body with `request.get_json(silent=True)`. If the result is `None` or not a dict, it raises `ValidationError`.
2. The route calls `service.create_task(title, description)`.
3. The service validates the types, trims the title, and rejects an empty one with `ValidationError`.
4. The service calls `repository.add(...)`. The repository takes the lock, assigns the next ID, stores the `Task` and returns it.
5. The route returns `jsonify(task.to_dict())` with status `201`.
6. If the service raised `ValidationError`, the registered handler returns `400` with `{"error": "<message>"}`.

### List tasks: `GET /tasks`

1. The route calls `service.list_tasks()`, which calls `repository.list()`. The result is a list of tasks in insertion order.
2. The route returns `jsonify([t.to_dict() for t in tasks])` with status `200`.

### Complete a task: `PATCH /tasks/<int:id>/complete`

1. The route calls `service.complete_task(id)`.
2. The service calls `repository.get(id)`. If the task is missing, the repository raises `TaskNotFoundError`.
3. The service sets `completed = True`, which is idempotent, and saves it through the repository.
4. The route returns the task with status `200`. `TaskNotFoundError` is mapped to `404` by the error handler.

### Delete a task: `DELETE /tasks/<int:id>`

1. The route calls `service.delete_task(id)`, which calls `repository.delete(id)`.
2. The repository removes the task, or raises `TaskNotFoundError` if it is absent.
3. The route returns an empty body with status `204`. `TaskNotFoundError` is mapped to `404`.

### Design rules

- **Dependency direction:** routes -> service -> repository -> model. Lower layers never import higher ones.
- **Errors:** the service and repository raise domain exceptions. Only the error handlers turn them into HTTP responses, which keeps the error format in one place.
- **Wiring:** `create_app()` builds `TaskRepository`, passes it to `TaskService`, and passes the service to the blueprint factory (`create_tasks_blueprint(service)`). There are no module-level globals, so every app instance and every test has its own storage.

## 5. Testing Approach

| Level | Target | Tool |
|---|---|---|
| Unit | `TaskRepository` (ID monotonicity, order, delete), `TaskService` (validation, idempotent complete) | pytest |
| API | Each endpoint and acceptance criterion in US-1 to US-5, through Flask's test client against a fresh `create_app()` | pytest + Flask test client |

## 6. Traceability

| Story | Endpoint | Components involved |
|---|---|---|
| US-1 Create | `POST /tasks` | Route, Service (validation), Repository (ID, store), Error handler (400) |
| US-2 List | `GET /tasks` | Route, Service, Repository (ordered read) |
| US-3 Complete | `PATCH /tasks/{id}/complete` | Route, Service, Repository, Error handler (404) |
| US-4 Delete | `DELETE /tasks/{id}` | Route, Service, Repository, Error handler (404) |
| US-5 Errors | all | Error handlers (400, 404, 405, 500) |
