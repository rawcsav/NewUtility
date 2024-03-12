import json
import os
from typing import Dict
from uuid import uuid1

from celery import Celery, Task
from flask import g, has_app_context, has_request_context, request


class ContextTask(Task):
    def dump_current_request_context(self, task_id) -> Dict:
        if not has_request_context():
            return None

        user = getattr(g, "flask_httpauth_user", None)
        context_info = {
            "method": request.method,
            "headers": dict(request.headers),
            "user_id": user.id if user else None,
        }

        redis = self.app.flask_app.extensions["redis"]
        db = self.app.flask_app.extensions["sqlalchemy"]
        # just spare
        redis.set(f"TASK_DUMP_REQUEST_CONTEXT::{task_id}", json.dumps(context_info))

        return context_info

    def apply_async(self, args=None, kwargs=None, **rest):
        task_id = self.request.id or uuid1().hex
        # Custom data will be passed with headers
        rest.update({"headers": self.dump_current_request_context(task_id), "task_id": task_id})
        return super().apply_async(args, kwargs, **rest)

    def apply(self, args=None, kwargs=None, **rest):
        task_id = self.request.id or uuid1().hex
        rest.update({"headers": self.dump_current_request_context(task_id), "task_id": task_id})
        return super().apply(args, kwargs, **rest)

    def retry(self, args=None, kwargs=None, **rest):
        task_id = self.request.id or uuid1().hex
        rest.update({"headers": self.dump_current_request_context(task_id), "task_id": task_id})
        return super().retry(args, kwargs, **rest)

    def __call__(self, *args, **kwargs):
        if has_app_context():
            os.environ["FLASK_CONTEXT_IN_CELERY"] = "true"
            return Task.__call__(self, *args, **kwargs)
        with self.app.flask_app.app_context():
            os.environ["FLASK_CONTEXT_IN_CELERY"] = "true"
            return Task.__call__(self, *args, **kwargs)
