from sqlalchemy import func, insert

from app import db
from app.models.mixins import generate_uuid


def after_update_listener(mapper, connection, target):
    if target.delete:
        deletion_task = Task(type="Deletion", status="pending", user_id=target.user_id)
        stmt = insert(Task).values(type=deletion_task.type, status=deletion_task.status, user_id=deletion_task.user_id)
        result = connection.execute(stmt)

        task_id = result.inserted_primary_key[0]

        stmt = insert(DeletionTask).values(task_id=task_id, entity_type=target.__tablename__, entity_id=target.id)
        from app.tasks.deletion_task import process_deletion_task

        process_deletion_task.apply_async(kwargs={"task_id": task_id})

        connection.execute(stmt)


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    type = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), default="pending")
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=False), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=False), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Task {self.id} {self.type} {self.status}>"


class DeletionTask(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))
    entity_type = db.Column(db.String(255))
    entity_id = db.Column(db.String(36))

    def __repr__(self):
        return f"<DeletionTask {self.id} - {self.entity_type}>"


class EmbeddingTask(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))  # Link to Task model
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    chunk_size = db.Column(db.Integer)
    temp_path = db.Column(db.String(255))
    advanced_preprocessing = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<EmbeddingTask {self.id} - {self.title}>"


class ImageTask(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))  # Link to Task model
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    quality = db.Column(db.String(50))
    style = db.Column(db.String(50))
    n = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f"<ImageTask {self.id} - {self.prompt[:30]}>"


class TTSTask(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))  # Link to Task model
    model = db.Column(db.String(50))
    voice = db.Column(db.String(50))
    input_text = db.Column(db.Text)
    response_format = db.Column(db.String(50))
    speed = db.Column(db.Float)

    def __repr__(self):
        return f"<TTSTask {self.id} - {self.input_text[:30]}>"


class TranscriptionTask(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))
    input_filename = db.Column(db.String(255))
    model = db.Column(db.String(50))
    prompt = db.Column(db.Text)
    response_format = db.Column(db.String(50))
    temperature = db.Column(db.Float)
    language = db.Column(db.String(2))

    def __repr__(self):
        return f"<TranscriptionTask - {self.input_filename[:30]}>"


class TranslationTask(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))
    input_filename = db.Column(db.String(255))
    model = db.Column(db.String(50))
    prompt = db.Column(db.Text)
    response_format = db.Column(db.String(50))
    temperature = db.Column(db.Float)

    def __repr__(self):
        return f"<TranslationTask {self.id} - {self.input_filename[:30]}>"
