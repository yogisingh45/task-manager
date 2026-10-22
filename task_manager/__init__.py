"""Task Manager API package."""

from flask import Flask

from task_manager.errors import register_error_handlers
from task_manager.repositories.task_repository import TaskRepository
from task_manager.routes.tasks import create_tasks_blueprint
from task_manager.services.task_service import TaskService


def create_app() -> Flask:
    """Build a Flask app with its own fresh in-memory storage."""
    app = Flask(__name__)
    service = TaskService(TaskRepository())
    app.register_blueprint(create_tasks_blueprint(service))
    register_error_handlers(app)
    return app
