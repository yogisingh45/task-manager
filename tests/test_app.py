"""API tests for the Task Manager, covering US-1 to US-5."""

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from task_manager import create_app
from task_manager.errors import TaskNotFoundError, ValidationError
from task_manager.repositories.task_repository import TaskRepository
from task_manager.services.task_service import TaskService


@pytest.fixture
def app() -> Flask:
    """Return a fresh app (and fresh storage) for each test."""
    return create_app()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Return a test client for the fresh app."""
    return app.test_client()


def make_task(client: FlaskClient, title: str = "Task", **extra: Any) -> dict[str, Any]:
    """Create a task through the API and return its JSON."""
    response = client.post("/tasks", json={"title": title, **extra})
    assert response.status_code == 201
    return response.get_json()


def assert_error(response: Any, status: int) -> None:
    """Assert a response is a JSON error with the given status."""
    assert response.status_code == status
    assert response.is_json
    body = response.get_json()
    assert set(body) == {"error"}
    assert isinstance(body["error"], str) and body["error"]


# ---------------------------------------------------------------- US-1 create


class TestCreate:
    """POST /tasks."""

    def test_create_with_title_only(self, client: FlaskClient) -> None:
        """A title-only task gets defaults and an ID."""
        response = client.post("/tasks", json={"title": "Buy milk"})
        assert response.status_code == 201
        assert response.get_json() == {
            "id": 1, "title": "Buy milk", "description": "", "completed": False,
        }

    def test_create_with_description(self, client: FlaskClient) -> None:
        """Title and description are both stored and returned."""
        response = client.post("/tasks", json={"title": "A", "description": "details"})
        assert response.status_code == 201
        assert response.get_json()["description"] == "details"

    def test_title_is_trimmed(self, client: FlaskClient) -> None:
        """Surrounding whitespace is stripped from the title."""
        assert make_task(client, "  padded  ")["title"] == "padded"

    def test_ids_are_unique_and_increasing(self, client: FlaskClient) -> None:
        """Each new task gets a different, increasing ID."""
        ids = [make_task(client, f"t{i}")["id"] for i in range(3)]
        assert ids == [1, 2, 3]

    def test_ids_not_reused_after_delete(self, client: FlaskClient) -> None:
        """Deleting the latest task does not free its ID."""
        make_task(client, "a")
        last = make_task(client, "b")
        client.delete(f"/tasks/{last['id']}")
        assert make_task(client, "c")["id"] == 3

    def test_extra_fields_are_ignored(self, client: FlaskClient) -> None:
        """Clients cannot set id or completed on creation."""
        task = make_task(client, "x", id=99, completed=True)
        assert task["id"] == 1
        assert task["completed"] is False

    @pytest.mark.parametrize("title", ["", "   ", "\t\n"])
    def test_empty_or_blank_title(self, client: FlaskClient, title: str) -> None:
        """Empty or whitespace-only titles are rejected and nothing is stored."""
        assert_error(client.post("/tasks", json={"title": title}), 400)
        assert client.get("/tasks").get_json() == []

    def test_missing_title(self, client: FlaskClient) -> None:
        """A body without a title is rejected."""
        assert_error(client.post("/tasks", json={"description": "x"}), 400)

    @pytest.mark.parametrize("title", [123, True, None, ["a"], {"a": 1}])
    def test_non_string_title(self, client: FlaskClient, title: Any) -> None:
        """Non-string titles are rejected."""
        assert_error(client.post("/tasks", json={"title": title}), 400)

    @pytest.mark.parametrize("description", [123, None, ["a"], False])
    def test_non_string_description(self, client: FlaskClient, description: Any) -> None:
        """Non-string descriptions are rejected and nothing is stored."""
        response = client.post("/tasks", json={"title": "ok", "description": description})
        assert_error(response, 400)
        assert client.get("/tasks").get_json() == []

    def test_invalid_json(self, client: FlaskClient) -> None:
        """A malformed JSON body is rejected."""
        response = client.post("/tasks", data="{not json", content_type="application/json")
        assert_error(response, 400)

    def test_no_body(self, client: FlaskClient) -> None:
        """A request with no body is rejected."""
        assert_error(client.post("/tasks"), 400)

    @pytest.mark.parametrize("body", [[], ["title"], "title", 5])
    def test_body_not_an_object(self, client: FlaskClient, body: Any) -> None:
        """A valid JSON body that is not an object is rejected."""
        assert_error(client.post("/tasks", json=body), 400)


# ------------------------------------------------------------------ US-2 read


class TestList:
    """GET /tasks."""

    def test_empty_list(self, client: FlaskClient) -> None:
        """No tasks yields 200 and an empty array."""
        response = client.get("/tasks")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_lists_in_creation_order_with_all_fields(self, client: FlaskClient) -> None:
        """Tasks come back in creation order with every field present."""
        for title in ["first", "second", "third"]:
            make_task(client, title)
        tasks = client.get("/tasks").get_json()
        assert [t["title"] for t in tasks] == ["first", "second", "third"]
        assert all(set(t) == {"id", "title", "description", "completed"} for t in tasks)

    def test_includes_completed_and_incomplete(self, client: FlaskClient) -> None:
        """Both completed and incomplete tasks are listed."""
        make_task(client, "a")
        make_task(client, "b")
        client.patch("/tasks/1/complete")
        completed = [t["completed"] for t in client.get("/tasks").get_json()]
        assert completed == [True, False]

    def test_deleted_task_not_listed(self, client: FlaskClient) -> None:
        """Deleted tasks disappear from the list."""
        make_task(client, "a")
        make_task(client, "b")
        client.delete("/tasks/1")
        assert [t["id"] for t in client.get("/tasks").get_json()] == [2]


# ------------------------------------------------------------- US-3 complete


class TestComplete:
    """PATCH /tasks/<id>/complete."""

    def test_complete_task(self, client: FlaskClient) -> None:
        """Completing returns the updated task and leaves other fields alone."""
        make_task(client, "Buy milk", description="2l")
        response = client.patch("/tasks/1/complete")
        assert response.status_code == 200
        assert response.get_json() == {
            "id": 1, "title": "Buy milk", "description": "2l", "completed": True,
        }

    def test_completion_is_persisted(self, client: FlaskClient) -> None:
        """A later list shows the task as completed."""
        make_task(client)
        client.patch("/tasks/1/complete")
        assert client.get("/tasks").get_json()[0]["completed"] is True

    def test_complete_is_idempotent(self, client: FlaskClient) -> None:
        """Completing twice returns 200 both times and stays completed."""
        make_task(client)
        first = client.patch("/tasks/1/complete")
        second = client.patch("/tasks/1/complete")
        assert first.status_code == second.status_code == 200
        assert second.get_json()["completed"] is True

    def test_does_not_affect_other_tasks(self, client: FlaskClient) -> None:
        """Completing one task leaves the others untouched."""
        make_task(client, "a")
        make_task(client, "b")
        client.patch("/tasks/1/complete")
        assert client.get("/tasks").get_json()[1]["completed"] is False

    @pytest.mark.parametrize("task_id", [0, 1, 999, -1])
    def test_nonexistent_id(self, client: FlaskClient, task_id: int) -> None:
        """Unknown IDs return a JSON 404."""
        response = client.patch(f"/tasks/{task_id}/complete")
        assert_error(response, 404)

    def test_not_found_message(self, client: FlaskClient) -> None:
        """The 404 body uses the documented message."""
        assert client.patch("/tasks/5/complete").get_json() == {"error": "Task not found"}

    def test_complete_deleted_task(self, client: FlaskClient) -> None:
        """A deleted task can no longer be completed."""
        make_task(client)
        client.delete("/tasks/1")
        assert_error(client.patch("/tasks/1/complete"), 404)


# ------------------------------------------------------------------ US-4 delete


class TestDelete:
    """DELETE /tasks/<id>."""

    def test_delete_task(self, client: FlaskClient) -> None:
        """Deleting returns 204 with no body and removes the task."""
        make_task(client)
        response = client.delete("/tasks/1")
        assert response.status_code == 204
        assert response.data == b""
        assert client.get("/tasks").get_json() == []

    def test_delete_twice(self, client: FlaskClient) -> None:
        """A repeated delete returns 404."""
        make_task(client)
        assert client.delete("/tasks/1").status_code == 204
        assert_error(client.delete("/tasks/1"), 404)

    def test_delete_nonexistent(self, client: FlaskClient) -> None:
        """Deleting an unknown ID returns a JSON 404."""
        response = client.delete("/tasks/42")
        assert_error(response, 404)
        assert response.get_json() == {"error": "Task not found"}

    def test_does_not_affect_other_tasks(self, client: FlaskClient) -> None:
        """Deleting one task leaves the others in place."""
        make_task(client, "a")
        make_task(client, "b")
        client.delete("/tasks/1")
        assert [t["title"] for t in client.get("/tasks").get_json()] == ["b"]


# ------------------------------------------------------------- US-5 errors


class TestErrorHandling:
    """Consistent JSON errors."""

    def test_unknown_route(self, client: FlaskClient) -> None:
        """Undefined routes return JSON 404, not HTML."""
        assert_error(client.get("/nope"), 404)

    @pytest.mark.parametrize("path", ["/tasks/abc", "/tasks/1.5", "/tasks/abc/complete"])
    def test_non_integer_id(self, client: FlaskClient, path: str) -> None:
        """Non-integer IDs do not match a route and return 404."""
        assert_error(client.delete(path) if "complete" not in path else client.patch(path), 404)

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("put", "/tasks"), ("delete", "/tasks"), ("patch", "/tasks"),
            ("get", "/tasks/1"), ("post", "/tasks/1"), ("put", "/tasks/1"),
            ("get", "/tasks/1/complete"), ("post", "/tasks/1/complete"),
            ("delete", "/tasks/1/complete"),
        ],
    )
    def test_method_not_allowed(self, client: FlaskClient, method: str, path: str) -> None:
        """Unsupported methods on defined routes return JSON 405."""
        assert_error(getattr(client, method)(path), 405)

    def test_unexpected_exception_returns_generic_500(self) -> None:
        """Unhandled errors give a generic 500 with no internal details."""
        app = create_app()
        app.testing = False  # let the handler run instead of propagating

        @app.get("/boom")
        def boom() -> str:
            """Raise an unexpected error."""
            raise RuntimeError("secret internal detail")

        response = app.test_client().get("/boom")
        assert_error(response, 500)
        assert "secret" not in response.get_data(as_text=True)
        assert "Traceback" not in response.get_data(as_text=True)

    def test_validation_error_hides_internals(self, client: FlaskClient) -> None:
        """Error bodies contain only the message."""
        body = client.post("/tasks", json={"title": ""}).get_json()
        assert list(body) == ["error"]

    def test_apps_have_isolated_storage(self) -> None:
        """Separate create_app() calls do not share tasks."""
        first, second = create_app().test_client(), create_app().test_client()
        make_task(first)
        assert second.get("/tasks").get_json() == []


# ---------------------------------------------------- service / repository units


class TestServiceAndRepository:
    """Unit tests below the HTTP layer."""

    def test_repository_missing_raises(self) -> None:
        """get/delete/save of a missing ID raise TaskNotFoundError."""
        repo = TaskRepository()
        with pytest.raises(TaskNotFoundError):
            repo.get(1)
        with pytest.raises(TaskNotFoundError):
            repo.delete(1)

    def test_repository_ids_monotonic(self) -> None:
        """IDs keep increasing after deletions."""
        repo = TaskRepository()
        repo.add("a")
        repo.delete(1)
        assert repo.add("b").id == 2

    def test_service_validation(self) -> None:
        """The service rejects blank and non-string input."""
        service = TaskService(TaskRepository())
        with pytest.raises(ValidationError):
            service.create_task("   ")
        with pytest.raises(ValidationError):
            service.create_task(5)
        with pytest.raises(ValidationError):
            service.create_task("ok", 5)

    def test_service_complete_idempotent(self) -> None:
        """Completing twice leaves the task completed."""
        service = TaskService(TaskRepository())
        task = service.create_task("a")
        service.complete_task(task.id)
        assert service.complete_task(task.id).completed is True
