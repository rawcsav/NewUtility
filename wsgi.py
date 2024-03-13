import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, socketio, celery
from app.tasks import audio_task, image_task, deletion_task, embedding_task, task_logging

app = create_app()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)
