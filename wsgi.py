import eventlet

eventlet.monkey_patch()

import os
from dotenv import load_dotenv


dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, socketio
from app.tasks.celery_task import make_celery


app = create_app()
celery = make_celery(app=app, socketio=socketio)

if __name__ == "__main__":
    FLASK_DEBUG = False
    socketio.run(app, host="localhost", port=8080)
