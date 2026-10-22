"""Entry point: ``flask --app app run`` or ``python app.py``."""

from task_manager import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
