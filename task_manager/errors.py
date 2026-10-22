"""Domain exceptions and the central error handlers that map them to JSON."""

from flask import Flask, jsonify
from flask.wrappers import Response
from werkzeug.exceptions import HTTPException


class ValidationError(Exception):
    """Raised when request data fails validation."""


class TaskNotFoundError(Exception):
    """Raised when no task exists with the requested ID."""


def _error_response(message: str, status: int) -> tuple[Response, int]:
    """Build the standard ``{"error": "<message>"}`` response."""
    return jsonify({"error": message}), status


def register_error_handlers(app: Flask) -> None:
    """Register handlers so every error is returned as consistent JSON."""

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> tuple[Response, int]:
        """Map ``ValidationError`` to 400."""
        return _error_response(str(error), 400)

    @app.errorhandler(TaskNotFoundError)
    def handle_not_found_error(error: TaskNotFoundError) -> tuple[Response, int]:
        """Map ``TaskNotFoundError`` to 404."""
        return _error_response("Task not found", 404)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
        """Map framework errors (unknown route, wrong method, ...) to JSON."""
        return _error_response(error.name, error.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
        """Map unhandled exceptions to a generic 500 with no internal details."""
        app.logger.exception("Unhandled exception")
        return _error_response("Internal server error", 500)
