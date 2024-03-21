from flask_socketio import SocketIO
from celery import Celery
from flask import Flask

celery = Celery(__name__)


def make_celery(app: Flask, socketio: SocketIO) -> Celery:
    celery.conf.broker_url = app.config["CELERY_BROKER_URL"]
    celery.conf.result_backend = app.config["CELERY_RESULT_BACKEND"]
    celery.conf.imports = app.config["CELERY_IMPORTS"]

    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True
        _socketio = None

        @property
        def socketio(self):
            if not self._socketio:
                self._socketio = socketio
            return self._socketio

        def emit_response(self, message, room, event_type="response", namespace=None):
            self.socketio.emit(event_type, {"message": message}, room=room, namespace=namespace)

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    celery.finalize()
    return celery
