# Task Manager API – User Stories

Personal Task Manager REST API built with Python and Flask. Tasks are stored in memory, so data is lost when the server restarts. All requests and responses use JSON.

## Task Model

| Field         | Type    | Notes                                      |
|---------------|---------|--------------------------------------------|
| `id`          | integer | Auto-generated, unique, never reused       |
| `title`       | string  | Required, non-empty                        |
| `description` | string  | Optional, defaults to an empty string      |
| `completed`   | boolean | Defaults to `false`                        |

## Assumptions

- Single user, so there is no authentication.
- Completing a task is one-way. Un-completing is out of scope.
- Endpoints: `POST /tasks`, `GET /tasks`, `PATCH /tasks/<id>/complete`, `DELETE /tasks/<id>`.

---

## US-1: Create a Task

**As a** user,
**I want to** create a new task with a title and an optional description,
**So that** I can record work I need to remember to do.

### Acceptance Criteria

1. `POST /tasks` with `{"title": "Buy milk"}` returns `201 Created` and the new task as JSON.
2. The created task has a unique auto-generated `id`, the supplied `title`, an empty `description`, and `completed` set to `false`.
3. `POST /tasks` with a `title` and a `description` stores and returns both.
4. If `title` is missing, empty, or only whitespace, the API returns `400 Bad Request` with a JSON error message, and no task is created.
5. If `title` or `description` is not a string, the API returns `400 Bad Request`.
6. If the request body is not valid JSON, the API returns `400 Bad Request`.
7. Each new task gets a different `id`, including after earlier tasks have been deleted.

---

## US-2: List All Tasks

**As a** user,
**I want to** see all of my tasks,
**So that** I can review what I have to do and what I have finished.

### Acceptance Criteria

1. `GET /tasks` returns `200 OK` and a JSON array of all tasks.
2. Each task includes `id`, `title`, `description`, and `completed`.
3. Both completed and incomplete tasks are returned.
4. Tasks are returned in creation order.
5. When no tasks exist, the API returns `200 OK` and an empty array `[]`.
6. Deleted tasks do not appear in the list.

---

## US-3: Mark a Task as Complete

**As a** user,
**I want to** mark a task as complete,
**So that** I can track my progress and tell finished work from outstanding work.

### Acceptance Criteria

1. `PATCH /tasks/<id>/complete` on an existing task returns `200 OK` and the updated task with `completed` set to `true`.
2. The change is persisted. A later `GET /tasks` shows the task as completed.
3. Other fields (`id`, `title`, `description`) are unchanged.
4. Completing an already-completed task is idempotent: it returns `200 OK` and the task stays completed.
5. If no task with the given `id` exists, the API returns `404 Not Found` with a JSON error message.
6. Completing one task does not affect any other task.

---

## US-4: Delete a Task

**As a** user,
**I want to** delete a task,
**So that** I can remove tasks that are no longer relevant or were created by mistake.

### Acceptance Criteria

1. `DELETE /tasks/<id>` on an existing task removes it and returns `204 No Content` with no body.
2. After deletion, `GET /tasks` no longer includes the task.
3. If no task with the given `id` exists, the API returns `404 Not Found` with a JSON error message.
4. Deleting the same task a second time returns `404 Not Found`.
5. Deleting one task does not affect any other task.

---

## US-5: Consistent JSON Error Handling

**As a** user or API client,
**I want** errors to come back in a predictable JSON format,
**So that** I can understand what went wrong and handle it programmatically.

### Acceptance Criteria

1. All error responses are JSON in the shape `{"error": "<message>"}`.
2. Validation failures return `400`, and unknown task IDs return `404`.
3. Requests to undefined routes return a JSON `404`, not an HTML page.
4. Requests with an unsupported method on a defined route return a JSON `405 Method Not Allowed`.
5. Error messages do not expose stack traces or internal details.

---

## Out of Scope

- Authentication and multiple users
- Persistent storage (database or file)
- Editing a task's title or description
- Un-completing a task
- Filtering, sorting, pagination, due dates, and priorities
