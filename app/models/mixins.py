import uuid
from sqlalchemy import func
from app import db


def generate_uuid():
    return str(uuid.uuid4())


class SoftDeleteMixin:
    delete = db.Column(db.Boolean, default=False, nullable=False)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
