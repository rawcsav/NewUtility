import json

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref

from app import db
from app.models.mixins import generate_uuid, SoftDeleteMixin, TimestampMixin


class TTSPreferences(db.Model):
    __tablename__ = "tts_preferences"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), unique=True, index=True)
    model = db.Column(db.Enum("tts-1", "tts-1-hd"), nullable=False, default="tts-1")
    voice = db.Column(db.Enum("alloy", "echo", "fable", "onyx", "nova", "shimmer"), nullable=False, default="alloy")
    response_format = db.Column(db.Enum("mp3", "opus", "aac", "flac"), nullable=False, default="mp3")
    speed = db.Column(db.Float, nullable=False, default=1.0)


class WhisperPreferences(db.Model):
    __tablename__ = "whisper_preferences"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), unique=True, index=True)
    model = db.Column(db.Enum("whisper-1"), nullable=False, default="whisper-1")
    language = db.Column(db.String(2), nullable=True, default="en")
    response_format = db.Column(db.Enum("json", "text", "srt", "verbose_json", "vtt"), nullable=False, default="text")
    temperature = db.Column(db.Float, nullable=False, default=0.0)


class TTSJob(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "tts_jobs"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))
    task = db.relationship("Task", backref=backref("tts_job", uselist=False))
    model = db.Column(db.Enum("tts-1", "tts-1-hd"), nullable=False)
    voice = db.Column(db.Enum("alloy", "echo", "fable", "onyx", "nova", "shimmer"), nullable=False)
    response_format = db.Column(db.Enum("mp3", "opus", "aac", "flac"), nullable=False)
    speed = db.Column(db.Float, nullable=False)
    input_text = db.Column(db.String(4096), nullable=False)
    output_filename = db.Column(db.String(255), nullable=True)
    user = db.relationship("User", back_populates="tts_jobs")


def _concatenate_vtt_segments(sorted_segments):
    header = "WEBVTT\n\n"
    body = "\n\n".join(segment.output_text for segment in sorted_segments)
    return header + body


def _concatenate_srt_segments(sorted_segments):
    return "\n\n".join(segment.output_content for segment in sorted_segments)


class TranscriptionJob(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "transcription_jobs"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))
    task = db.relationship("Task", backref=backref("transcription_job", uselist=False))
    prompt = db.Column(db.Text, nullable=True)
    model = db.Column(db.Enum("whisper-1"), nullable=False)
    language = db.Column(db.String(2), nullable=True)
    response_format = db.Column(db.Enum("json", "text", "srt", "verbose_json", "vtt"), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    input_filename = db.Column(db.String(255), nullable=False)
    finished = db.Column(db.Boolean, nullable=False, default=False)
    segments = db.relationship(
        "TranscriptionJobSegment",
        order_by="TranscriptionJobSegment.job_index",
        back_populates="transcription_job",
        cascade="all, delete-orphan",
    )
    user = db.relationship("User", back_populates="transcription_jobs")

    @hybrid_property
    def final_content(self):
        return self._generate_concatenated_output()

    def _generate_concatenated_output(self):
        sorted_segments = sorted(self.segments, key=lambda seg: seg.job_index)
        if self.response_format in ["json", "verbose_json"]:
            return json.dumps([json.loads(segment.output_content) for segment in sorted_segments])
        elif self.response_format == "text":
            return "\n".join(segment.output_content for segment in sorted_segments)
        elif self.response_format == "srt":
            return _concatenate_srt_segments(sorted_segments)
        elif self.response_format == "vtt":
            return _concatenate_vtt_segments(sorted_segments)
        else:
            return "\n".join(segment.output_text for segment in sorted_segments)


class TranslationJob(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "translation_jobs"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    task_id = db.Column(db.String(36), db.ForeignKey("task.id"))
    task = db.relationship("Task", backref=backref("translation_job", uselist=False))
    prompt = db.Column(db.Text, nullable=True)
    model = db.Column(db.Enum("whisper-1"), nullable=False)
    response_format = db.Column(db.Enum("json", "text", "srt", "verbose_json", "vtt"), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    input_filename = db.Column(db.String(255), nullable=False)
    finished = db.Column(db.Boolean, nullable=False, default=False)
    segments = db.relationship(
        "TranslationJobSegment",
        order_by="TranslationJobSegment.job_index",
        back_populates="translation_job",
        cascade="all, delete-orphan",
    )
    user = db.relationship("User", back_populates="translation_jobs")

    @hybrid_property
    def final_content(self):
        return self._generate_concatenated_output()

    def _generate_concatenated_output(self):
        sorted_segments = sorted(self.segments, key=lambda seg: seg.job_index)

        if self.response_format in ["json", "verbose_json"]:
            return json.dumps([json.loads(segment.output_content) for segment in sorted_segments])
        elif self.response_format == "text":
            return "\n".join(segment.output_content for segment in sorted_segments)
        elif self.response_format == "srt":
            return _concatenate_srt_segments(sorted_segments)
        elif self.response_format == "vtt":
            return _concatenate_vtt_segments(sorted_segments)
        else:
            return "\n".join(segment.output_text for segment in sorted_segments)


class TranscriptionJobSegment(db.Model):
    __tablename__ = "transcription_job_segments"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    transcription_job_id = db.Column(
        db.String(36), db.ForeignKey("transcription_jobs.id", ondelete="CASCADE"), index=True
    )
    duration = db.Column(db.Float, nullable=False)
    output_content = db.Column(db.Text, nullable=False)
    job_index = db.Column(db.Integer, nullable=False)
    transcription_job = db.relationship("TranscriptionJob", back_populates="segments")


class TranslationJobSegment(db.Model):
    __tablename__ = "translation_job_segments"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    translation_job_id = db.Column(db.String(36), db.ForeignKey("translation_jobs.id", ondelete="CASCADE"), index=True)
    duration = db.Column(db.Float, nullable=False)
    output_content = db.Column(db.Text, nullable=False)
    job_index = db.Column(db.Integer, nullable=False)
    translation_job = db.relationship("TranslationJob", back_populates="segments")
