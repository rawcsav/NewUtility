from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.sql import func

db = SQLAlchemy()


class UserAPIKey(db.Model):
    __tablename__ = 'user_api_keys'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    encrypted_api_key = db.Column(db.String(255), nullable=False)
    label = db.Column(db.String(50))  # Optional label for the key
    models = db.Column(db.String(255))  # New field to store accessible models
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    openai_api_key = db.Column(db.String(255),
                               nullable=True)  # Make nullable if storing API keys is optional
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    confirmation_code = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    login_attempts = db.Column(db.Integer, default=0)
    last_attempt_time = db.Column(db.DateTime)
    last_username_change = db.Column(db.DateTime)
    login_method = db.Column(db.String(10), nullable=False, default='None')

    selected_api_key_id = db.Column(db.Integer, db.ForeignKey('user_api_keys.id'),
                                    nullable=True)  # Make nullable if not all users have API keys

    # Relationships
    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    audio_files = db.relationship('AudioFile', backref='user', lazy='dynamic')
    document_embeddings = db.relationship('DocumentEmbedding', backref='user',
                                          lazy='dynamic')
    translations = db.relationship('Translation', backref='user', lazy='dynamic')
    api_usage = db.relationship('APIUsage', backref='user', lazy='dynamic')
    user_models = db.relationship('UserModel', backref='user', lazy='dynamic')
    speeches = db.relationship('Speech', backref='user', lazy='dynamic')
    api_keys = db.relationship('UserAPIKey', backref='user', lazy='dynamic',
                               foreign_keys=[UserAPIKey.user_id])
    selected_api_key = db.relationship('UserAPIKey', foreign_keys=[selected_api_key_id])


class UserModel(db.Model):
    __tablename__ = 'user_models'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    model_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy='dynamic')


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'))
    content = db.Column(db.Text, nullable=False)
    direction = db.Column(db.Enum('incoming', 'outgoing'), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    is_knowledge_query = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class AudioFile(db.Model):
    __tablename__ = 'audio_files'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    file_path = db.Column(db.String(255), nullable=False)
    transcription = db.Column(db.Text)
    language = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class DocumentEmbedding(db.Model):
    __tablename__ = 'document_embeddings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    document = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.Text,
                          nullable=False)  # Changed to Text type for JSON storage
    chunk_index = db.Column(db.Integer, nullable=False,
                            default=0)  # To support chunked embeddings
    model = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class Translation(db.Model):
    __tablename__ = 'translations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    source_text = db.Column(db.Text, nullable=False)
    translated_text = db.Column(db.Text, nullable=False)
    source_language = db.Column(db.String(10), nullable=False)
    target_language = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class APIUsage(db.Model):
    __tablename__ = 'api_usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    endpoint = db.Column(db.String(50), nullable=False)
    request_payload = db.Column(db.Text)
    response_payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class Speech(db.Model):
    __tablename__ = 'speeches'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    text = db.Column(db.Text, nullable=False)
    voice = db.Column(db.String(50), nullable=False)
    audio_data = db.Column(db.Text,
                           nullable=False)  # Assuming audio data is stored as base64 string
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
