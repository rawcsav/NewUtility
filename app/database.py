import uuid

from flask_login import UserMixin
from sqlalchemy import BLOB
from sqlalchemy.orm import backref
from sqlalchemy.sql import func

from app import db


def generate_uuid():
    return str(uuid.uuid4())


class SoftDeleteMixin:
    delete = db.Column(db.Boolean, default=False, nullable=False)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())


def generate_default_nickname():
    max_number = db.session.query(db.func.max(UserAPIKey.nickname)).scalar()
    next_number = int(max_number or 0) + 1  # Increment the max number by 1
    return f"User{next_number}"


class MessageChunkAssociation(db.Model):
    __tablename__ = "message_chunk_association"

    message_id = db.Column(
        db.String(36), db.ForeignKey("messages.id"), primary_key=True
    )
    chunk_id = db.Column(
        db.String(36),
        db.ForeignKey("document_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    similarity_rank = db.Column(db.Integer, nullable=False)  # Store the ranking here

    message = db.relationship("Message", back_populates="chunk_associations")
    chunk = db.relationship("DocumentChunk", back_populates="message_associations")


class UserAPIKey(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "user_api_keys"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    nickname = db.Column(
        db.String(25), nullable=False, default=generate_default_nickname
    )
    identifier = db.Column(db.String(6), nullable=False)
    encrypted_api_key = db.Column(BLOB, nullable=False)
    label = db.Column(db.String(50))
    api_key_token = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    usage_image_gen = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_chat = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_embedding = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_audio = db.Column(db.Numeric(10, 5), default=0, nullable=False)


class TierLimit(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    role_id = db.Column(db.String(36), db.ForeignKey("role.id"))
    max_audio_file_size = db.Column(db.Integer)  # in bytes
    max_audio_jobs = db.Column(db.Integer)
    audio_expiration = db.Column(db.Integer)  # in days
    max_chat_history = db.Column(db.Integer)  # number of conversations
    chat_expiration = db.Column(db.Integer)  # in days
    max_embed_file_size = db.Column(db.Integer)  # in bytes
    max_embed_concurrent_files = db.Column(db.Integer)
    embed_expiration = db.Column(db.Integer)  # in days
    image_limit_per_hour = db.Column(db.Integer)
    image_expiration = db.Column(db.Integer)  # in days


class Role(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(80), unique=True)
    limits = db.relationship("TierLimit", backref="role", uselist=False)

    def __init__(self, name):
        self.name = name


class User(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    confirmation_code = db.Column(db.String(6))
    login_attempts = db.Column(db.Integer, default=0)
    last_attempt_time = db.Column(db.DateTime)
    last_username_change = db.Column(db.DateTime)
    login_method = db.Column(db.String(10), nullable=False, default="None")
    reset_token_hash = db.Column(db.String(255), nullable=True)
    color_mode = db.Column(db.String(10), nullable=False, default="dark")

    selected_api_key_id = db.Column(
        db.String(36),
        db.ForeignKey("user_api_keys.id", ondelete="CASCADE"),
        nullable=True,
    )

    conversations = db.relationship(
        "Conversation",
        primaryjoin="and_(User.id==Conversation.user_id, Conversation.delete==False)",
        backref="user",
        lazy="dynamic"
    )
    document_embeddings = db.relationship(
        "DocumentEmbedding", backref="user", lazy="dynamic"
    )
    documents = db.relationship(
        "Document",
        primaryjoin="and_(User.id==Document.user_id, Document.delete==False)",
        backref="user",
        lazy="dynamic"
    )
    api_usage = db.relationship("APIUsage", backref="user", lazy="dynamic")
    api_keys = db.relationship(
        "UserAPIKey",
        primaryjoin="and_(User.id==UserAPIKey.user_id, UserAPIKey.delete==False)",
        backref="user",
        lazy="dynamic"
    )
    role_id = db.Column(db.String(36), db.ForeignKey("role.id"))
    role = db.relationship("Role", backref=db.backref("users", lazy="dynamic"))
    selected_api_key = db.relationship("UserAPIKey", foreign_keys=[selected_api_key_id])
    generated_images = db.relationship(
        "GeneratedImage",
        primaryjoin="and_(User.id==GeneratedImage.user_id, GeneratedImage.delete==False)",
        back_populates="user",
        lazy="dynamic"
    )
    chat_preferences = db.relationship(
        "ChatPreferences", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    tts_preferences = db.relationship(
        "TTSPreferences", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    whisper_preferences = db.relationship(
        "WhisperPreferences",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    tts_jobs = db.relationship(
        "TTSJob",
        primaryjoin="and_(User.id==TTSJob.user_id, TTSJob.delete==False)",
        back_populates="user",
        lazy="dynamic"
    )
    transcription_jobs = db.relationship(
        "TranscriptionJob",
        primaryjoin="and_(User.id==TranscriptionJob.user_id, TranscriptionJob.delete==False)",
        back_populates="user",
        lazy="dynamic"
    )
    translation_jobs = db.relationship(
        "TranslationJob",
        primaryjoin="and_(User.id==TranslationJob.user_id, TranslationJob.delete==False)",
        back_populates="user",
        lazy="dynamic"
    )

    def __init__(self, username, email, password_hash, **kwargs):
        super(User, self).__init__(**kwargs)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        if "role" not in kwargs:
            self.role = Role.query.filter_by(name="").first()


class Conversation(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "conversations"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(255), nullable=True, default="New Conversation")
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    system_prompt = db.Column(
        db.String(2048), nullable=True
    )  # New field for system prompts
    last_checked_time = db.Column(db.DateTime(timezone=False))
    is_interrupted = db.Column(db.Boolean, default=False)
    messages = db.relationship(
        "Message",
        primaryjoin="and_(Conversation.id==Message.conversation_id, Message.delete==False)",
        backref="conversation",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )


class Message(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "messages"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    conversation_id = db.Column(
        db.String(36), db.ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    content = db.Column(db.Text, nullable=False)
    direction = db.Column(db.Enum("incoming", "outgoing"), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    is_knowledge_query = db.Column(db.Boolean, default=False)
    is_voice = db.Column(db.Boolean, default=False)
    is_vision = db.Column(db.Boolean, default=False)
    is_error = db.Column(db.Boolean, default=False)
    message_images = db.relationship(
        "MessageImages",
        primaryjoin="and_(Message.id==MessageImages.message_id, MessageImages.delete==False)",
        backref="message",
        lazy="joined",
        cascade="all, delete-orphan"
    )
    chunk_associations = db.relationship(
        "MessageChunkAssociation",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ModelContextWindow(db.Model):
    __tablename__ = "model_context_windows"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    model_name = db.Column(db.String(50), nullable=False, unique=True)
    context_window_size = db.Column(db.Integer, nullable=False)


class ChatPreferences(db.Model):
    __tablename__ = "chat_preferences"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), unique=True, index=True
    )
    model = db.Column(db.String(50), default="gpt-3.5-turbo")
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=2000)
    frequency_penalty = db.Column(db.Float, default=0.0)
    presence_penalty = db.Column(db.Float, default=0.0)
    top_p = db.Column(db.Float, default=1.0)
    voice_mode = db.Column(db.Boolean, default=False)
    voice_model = db.Column(db.String(50), default="alloy")
    knowledge_query_mode = db.Column(db.Boolean, default=False)
    knowledge_context_tokens = db.Column(db.Integer, default=30)


class Document(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "documents"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=True)
    total_tokens = db.Column(db.Integer, nullable=False)
    pages = db.Column(db.String(25), nullable=True)
    selected = db.Column(db.Boolean, default=False)
    chunks = db.relationship(
        "DocumentChunk",
        back_populates="document",
        order_by="DocumentChunk.chunk_index",
        cascade="all, delete, delete-orphan",
        primaryjoin="and_(Document.id==DocumentChunk.document_id, Document.delete==False)"
    )


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = db.Column(db.Integer, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    tokens = db.Column(db.Integer, nullable=False)
    pages = db.Column(db.Integer, nullable=True)
    document = db.relationship("Document", back_populates="chunks")
    embedding = db.relationship(
        "DocumentEmbedding",
        back_populates="chunk",
        uselist=False,  # Important for one-to-one relationship
        cascade="all, delete, delete-orphan",
    )
    message_associations = db.relationship(
        "MessageChunkAssociation", back_populates="chunk", cascade="all, delete-orphan"
    )
    __table_args__ = (
        db.Index(
            "ix_document_chunks_document_id_chunk_index", "document_id", "chunk_index"
        ),
    )


class DocumentEmbedding(db.Model, TimestampMixin):
    __tablename__ = "document_embeddings"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    chunk_id = db.Column(
        db.String(36),
        db.ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    chunk = db.relationship("DocumentChunk", back_populates="embedding")
    embedding = db.Column(db.LargeBinary, nullable=False)
    model = db.Column(db.String(50), nullable=False)
    document = db.relationship(
        "Document",
        secondary="document_chunks",
        primaryjoin="DocumentEmbedding.chunk_id==DocumentChunk.id",
        secondaryjoin="and_(DocumentChunk.document_id==Document.id, Document.delete==False)",
        viewonly=True,
        backref=backref("embeddings", cascade="all, delete-orphan")
    )


class APIUsage(db.Model):
    __tablename__ = "api_usage"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    usage_image_gen = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_chat = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_embedding = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_audio = db.Column(db.Numeric(10, 5), default=0, nullable=False)


class GeneratedImage(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "generated_images"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    quality = db.Column(db.String(50), nullable=True)
    style = db.Column(db.String(50), nullable=True)
    user = db.relationship("User", back_populates="generated_images")


class MessageImages(db.Model, SoftDeleteMixin):
    __tablename__ = "message_images"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    uuid = db.Column(db.String(255), nullable=False, unique=True)
    image_url = db.Column(db.String(255), nullable=False)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    conversation_id = db.Column(
        db.String(36), db.ForeignKey("conversations.id", ondelete="CASCADE")
    )
    message_id = db.Column(
        db.String(36),
        db.ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user = db.relationship("User", backref="message_images", lazy="joined")
    conversation = db.relationship(
        "Conversation", backref="message_images", lazy="joined"
    )


class TTSPreferences(db.Model):
    __tablename__ = "tts_preferences"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), unique=True, index=True
    )
    model = db.Column(db.Enum("tts-1", "tts-1-hd"), nullable=False, default="tts-1")
    voice = db.Column(
        db.Enum("alloy", "echo", "fable", "onyx", "nova", "shimmer"),
        nullable=False,
        default="alloy",
    )
    response_format = db.Column(
        db.Enum("mp3", "opus", "aac", "flac"), nullable=False, default="mp3"
    )
    speed = db.Column(db.Float, nullable=False, default=1.0)


class WhisperPreferences(db.Model):
    __tablename__ = "transcription_preferences"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), unique=True, index=True
    )
    model = db.Column(db.Enum("whisper-1"), nullable=False, default="whisper-1")
    language = db.Column(db.String(2), nullable=True, default="en")
    response_format = db.Column(
        db.Enum("json", "text", "srt", "verbose_json", "vtt"),
        nullable=False,
        default="text",
    )
    temperature = db.Column(db.Float, nullable=False, default=0.0)

class TTSJob(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "tts_jobs"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    model = db.Column(db.Enum("tts-1", "tts-1-hd"), nullable=False)
    voice = db.Column(
        db.Enum("alloy", "echo", "fable", "onyx", "nova", "shimmer"), nullable=False
    )
    response_format = db.Column(
        db.Enum("mp3", "opus", "aac", "flac"), nullable=False
    )
    speed = db.Column(db.Float, nullable=False)
    input_text = db.Column(db.String(4096), nullable=False)
    final_output_path = db.Column(db.String(255), nullable=True)
    user = db.relationship("User", back_populates="tts_jobs")


class TranscriptionJob(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "transcription_jobs"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    prompt= db.Column(db.Text, nullable=False)
    model = db.Column(db.Enum("whisper-1"), nullable=False)
    language = db.Column(db.String(2), nullable=True)
    response_format = db.Column(
        db.Enum("json", "text", "srt", "verbose_json", "vtt"),
        nullable=False,
    )
    temperature = db.Column(db.Float, nullable=False)
    final_output_path = db.Column(db.String(255), nullable=True)
    segments = db.relationship("TranscriptionJobSegment", order_by="TranscriptionJobSegment.job_index", back_populates="transcription_job", cascade="all, delete-orphan")
    user = db.relationship("User", back_populates="transcription_jobs")


class TranslationJob(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "translation_jobs"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    prompt= db.Column(db.Text, nullable=False)
    model = db.Column(db.Enum("whisper-1"), nullable=False)
    response_format = db.Column(
        db.Enum("json", "text", "srt", "verbose_json", "vtt"),
        nullable=False,
    )
    temperature = db.Column(db.Float, nullable=False)
    final_output_path = db.Column(db.String(255), nullable=True)
    segments = db.relationship("TranslationJobSegment", order_by="TranslationJobSegment.job_index", back_populates="translation_job", cascade="all, delete-orphan")
    user = db.relationship("User", back_populates="translation_jobs")


class TranscriptionJobSegment(db.Model):
    __tablename__ = "transcription_job_segments"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    transcription_job_id = db.Column(
        db.String(36), db.ForeignKey("transcription_jobs.id", ondelete="CASCADE")
    )
    input_file_path = db.Column(db.String(255), nullable=False)
    output_file_path = db.Column(db.String(255), nullable=False)
    job_index = db.Column(db.Integer, nullable=False)
    transcription_job = db.relationship("TranscriptionJob", back_populates="segments")

class TranslationJobSegment(db.Model):
    __tablename__ = "translation_job_segments"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    translation_job_id = db.Column(
        db.String(36), db.ForeignKey("translation_jobs.id", ondelete="CASCADE")
    )
    input_file_path = db.Column(db.String(255), nullable=False)
    output_file_path = db.Column(db.String(255), nullable=False)
    job_index = db.Column(db.Integer, nullable=False)
    translation_job = db.relationship("TranslationJob", back_populates="segments")

def initialize_roles_with_limits():
    tier_limits = {
        "Guest": TierLimit(
            max_audio_file_size=20 * 1024 * 1024,
            max_audio_jobs=3,
            audio_expiration=1,
            max_chat_history=2,
            chat_expiration=24,
            max_embed_file_size=15 * 1024 * 1024,
            max_embed_concurrent_files=3,
            embed_expiration=24,
            image_limit_per_hour=5,
            image_expiration=12,
        ),
        "User": TierLimit(
            max_audio_file_size=25 * 1024 * 1024,
            max_audio_jobs=5,
            audio_expiration=24,
            max_chat_history=3,
            chat_expiration=48,
            max_embed_file_size=30 * 1024 * 1024,
            max_embed_concurrent_files=4,
            embed_expiration=48,
            image_limit_per_hour=10,
            image_expiration=24,
        ),
        "Premium": TierLimit(
            max_audio_file_size=60 * 1024 * 1024,
            max_audio_jobs=8,
            audio_expiration=96,  # 14 days
            max_chat_history=5,
            chat_expiration=120,  # 120 hours
            max_embed_file_size=60 * 1024 * 1024,
            max_embed_concurrent_files=8,
            embed_expiration=120,  # 96 hours
            image_limit_per_hour=15,
            image_expiration=120,  # 72 hours
        ),
        "Gang": TierLimit(
            max_audio_file_size=0,
            max_audio_jobs=0,
            audio_expiration=0,
            max_chat_history=0,
            chat_expiration=0,
            max_embed_file_size=0,
            max_embed_concurrent_files=0,
            embed_expiration=0,  # 120 hours
            image_limit_per_hour=0,
            image_expiration=0,  # 96 hours
        ),
    }

    for tier_name, limits in tier_limits.items():
        role = Role.query.filter_by(name=tier_name).first()
        if not role:
            role = Role(name=tier_name)
            db.session.add(role)
            db.session.flush()  # To get the role.id for the foreign key
            limits.role_id = role.id
            db.session.add(limits)
    db.session.commit()
