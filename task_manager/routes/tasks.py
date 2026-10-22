"""HTTP routes for the /tasks resource."""

from flask import Blueprint, request
from flask.wrappers import Response
from flask import jsonify

from task_manager.errors import ValidationError
from task_manager.services.task_service import TaskService


def create_tasks_blueprint(service: TaskService) -> Blueprint:
    """Build the tasks blueprint bound to the given service."""
    bp = Blueprint("tasks", __name__)

    @bp.post("/tasks")
    def create_task() -> tuple[Response, int]:
        """Create a task from a JSON body."""
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValidationError("request body must be a JSON object")
        task = service.create_task(body.get("title"), body.get("description", ""))
        return jsonify(task.to_dict()), 201

    @bp.get("/tasks")
    def list_tasks() -> tuple[Response, int]:
        """List all tasks."""
        return jsonify([t.to_dict() for t in service.list_tasks()]), 200

    @bp.patch("/tasks/<int:task_id>/complete")
    def complete_task(task_id: int) -> tuple[Response, int]:
        """Mark a task complete."""
        return jsonify(service.complete_task(task_id).to_dict()), 200

    @bp.delete("/tasks/<int:task_id>")
    def delete_task(task_id: int) -> tuple[str, int]:
        """Delete a task."""
        service.delete_task(task_id)
        return "", 204

    return bp
