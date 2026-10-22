"""The Task data model."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Task:
    """A single to-do item."""

    id: int
    title: str
    description: str = ""
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task to a JSON-compatible dict."""
        return asdict(self)
