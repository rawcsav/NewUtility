import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, socketio

app = create_app()
celery = app.extensions["celery"]
app.app_context().push()

from app.tasks import audio_task, image_task, deletion_task, embedding_task, task_logging


if __name__ == "__main__":
    socketio.run(app.run(port=8080, host="localhost"))
