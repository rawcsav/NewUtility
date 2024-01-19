import uuid

from flask_login import UserMixin
from sqlalchemy import BLOB

from app import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, generate_uuid


def generate_default_nickname():
    max_number = db.session.query(db.func.max(UserAPIKey.nickname)).scalar()
    next_number = int(max_number or 0) + 1  # Increment the max number by 1
    return f"User{next_number}"


class UserAPIKey(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "user_api_keys"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True)
    nickname = db.Column(db.String(25), nullable=False, default=generate_default_nickname)
    identifier = db.Column(db.String(6), nullable=False)
    encrypted_api_key = db.Column(BLOB, nullable=False)
    label = db.Column(db.String(50))
    api_key_token = db.Column(db.String(64), nullable=False, default=lambda: str(uuid.uuid4()))
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


class User(UserMixin, SoftDeleteMixin, db.Model, TimestampMixin):
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

    selected_api_key_id = db.Column(db.String(36), db.ForeignKey("user_api_keys.id"), nullable=True)

    conversations = db.relationship(
        "Conversation",
        primaryjoin="and_(User.id==Conversation.user_id, Conversation.delete==False)",
        backref="user",
        lazy="dynamic",
    )
    document_embeddings = db.relationship("DocumentEmbedding", backref="user", lazy="dynamic")
    documents = db.relationship(
        "Document",
        primaryjoin="and_(User.id==Document.user_id, Document.delete==False)",
        backref="user",
        lazy="dynamic",
    )
    api_usage = db.relationship("APIUsage", backref="user", lazy="dynamic")
    api_keys = db.relationship(
        "UserAPIKey",
        primaryjoin="and_(User.id==UserAPIKey.user_id, UserAPIKey.delete==False)",
        backref="user",
        lazy="dynamic",
    )
    role_id = db.Column(db.String(36), db.ForeignKey("role.id"))
    role = db.relationship("Role", backref=db.backref("users", lazy="dynamic"))
    selected_api_key = db.relationship("UserAPIKey", foreign_keys=[selected_api_key_id])
    generated_images = db.relationship(
        "GeneratedImage",
        primaryjoin="and_(User.id==GeneratedImage.user_id, GeneratedImage.delete==False)",
        back_populates="user",
        lazy="dynamic",
    )
    chat_preferences = db.relationship("ChatPreferences", backref="user", uselist=False, cascade="all, delete-orphan")
    tts_preferences = db.relationship("TTSPreferences", backref="user", uselist=False, cascade="all, delete-orphan")
    whisper_preferences = db.relationship(
        "WhisperPreferences", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    tts_jobs = db.relationship(
        "TTSJob",
        primaryjoin="and_(User.id==TTSJob.user_id, TTSJob.delete==False)",
        back_populates="user",
        lazy="dynamic",
    )
    transcription_jobs = db.relationship(
        "TranscriptionJob",
        primaryjoin="and_(User.id==TranscriptionJob.user_id, TranscriptionJob.delete==False)",
        back_populates="user",
        lazy="dynamic",
    )
    translation_jobs = db.relationship(
        "TranslationJob",
        primaryjoin="and_(User.id==TranslationJob.user_id, TranslationJob.delete==False)",
        back_populates="user",
        lazy="dynamic",
    )

    def __init__(self, username, email, password_hash, **kwargs):
        super(User, self).__init__(**kwargs)
        self.username = username
        self.email = email
        self.password_hash = password_hash
        if "role" not in kwargs:
            self.role = Role.query.filter_by(name="").first()


class APIUsage(db.Model):
    __tablename__ = "api_usage"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    usage_image_gen = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_chat = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_embedding = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_audio = db.Column(db.Numeric(10, 5), default=0, nullable=False)


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
