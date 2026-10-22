"""In-memory task storage."""

import threading

from task_manager.errors import TaskNotFoundError
from task_manager.models.task import Task


class TaskRepository:
    """Holds tasks in a dict and generates unique, never-reused IDs."""

    def __init__(self) -> None:
        """Create an empty repository."""
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1
        self._lock = threading.Lock()

    def add(self, title: str, description: str = "") -> Task:
        """Create and store a new task with the next ID."""
        with self._lock:
            task = Task(id=self._next_id, title=title, description=description)
            self._next_id += 1
            self._tasks[task.id] = task
            return task

    def get(self, task_id: int) -> Task:
        """Return the task with the given ID or raise ``TaskNotFoundError``."""
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError:
                raise TaskNotFoundError(task_id) from None

    def list(self) -> list[Task]:
        """Return all tasks in creation order."""
        with self._lock:
            return list(self._tasks.values())

    def save(self, task: Task) -> Task:
        """Persist changes to an existing task or raise ``TaskNotFoundError``."""
        with self._lock:
            if task.id not in self._tasks:
                raise TaskNotFoundError(task.id)
            self._tasks[task.id] = task
            return task

    def delete(self, task_id: int) -> None:
        """Remove the task with the given ID or raise ``TaskNotFoundError``."""
        with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(task_id)
            del self._tasks[task_id]
