"""Business rules for tasks. Contains no Flask imports."""

from typing import Any

from task_manager.errors import ValidationError
from task_manager.models.task import Task
from task_manager.repositories.task_repository import TaskRepository


class TaskService:
    """Validates input and coordinates task operations."""

    def __init__(self, repository: TaskRepository) -> None:
        """Create a service backed by the given repository."""
        self._repository = repository

    def create_task(self, title: Any, description: Any = "") -> Task:
        """Validate input and create a task.

        Raises ``ValidationError`` if the title is not a non-blank string or
        the description is not a string.
        """
        if not isinstance(title, str):
            raise ValidationError("title must be a string")
        title = title.strip()
        if not title:
            raise ValidationError("title is required and must not be empty")
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        return self._repository.add(title, description)

    def list_tasks(self) -> list[Task]:
        """Return all tasks in creation order."""
        return self._repository.list()

    def complete_task(self, task_id: int) -> Task:
        """Mark a task complete (idempotent) and return it."""
        task = self._repository.get(task_id)
        task.completed = True
        return self._repository.save(task)

    def delete_task(self, task_id: int) -> None:
        """Delete a task, raising ``TaskNotFoundError`` if it is missing."""
        self._repository.delete(task_id)
