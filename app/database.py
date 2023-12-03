import uuid
from flask_login import UserMixin
from sqlalchemy import BLOB
from sqlalchemy.sql import func
from app import db


class UserAPIKey(db.Model):
    __tablename__ = 'user_api_keys'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    nickname = db.Column(db.String(25), nullable=False)
    identifier = db.Column(db.String(6), nullable=False)
    encrypted_api_key = db.Column(BLOB, nullable=False)
    label = db.Column(db.String(50))
    api_key_token = db.Column(db.String(64), unique=True, nullable=False,
                              default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    confirmation_code = db.Column(db.String(6))
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
    login_attempts = db.Column(db.Integer, default=0)
    last_attempt_time = db.Column(db.DateTime)
    last_username_change = db.Column(db.DateTime)
    login_method = db.Column(db.String(10), nullable=False, default='None')
    reset_token_hash = db.Column(db.String(255), nullable=True)
    color_mode = db.Column(db.String(10), nullable=False, default='dark')

    selected_api_key_id = db.Column(db.Integer, db.ForeignKey('user_api_keys.id'),
                                    nullable=True)

    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    audio_files = db.relationship('AudioFile', backref='user', lazy='dynamic')
    document_embeddings = db.relationship('DocumentEmbedding', backref='user',
                                          lazy='dynamic')
    documents = db.relationship('Document', backref='user', lazy='dynamic')
    translations = db.relationship('Translation', backref='user', lazy='dynamic')
    api_usage = db.relationship('APIUsage', backref='user', lazy='dynamic')
    speeches = db.relationship('Speech', backref='user', lazy='dynamic')
    api_keys = db.relationship('UserAPIKey', backref='user', lazy='dynamic',
                               foreign_keys=[UserAPIKey.user_id])
    selected_api_key = db.relationship('UserAPIKey', foreign_keys=[selected_api_key_id])
    generated_images = db.relationship('GeneratedImage', back_populates='user',
                                       lazy='dynamic')


class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())

    messages = db.relationship('Message', backref='conversation', lazy='dynamic')


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'))
    content = db.Column(db.Text, nullable=False)
    direction = db.Column(db.Enum('incoming', 'outgoing'), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    is_knowledge_query = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())


class AudioFile(db.Model):
    __tablename__ = 'audio_files'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    file_path = db.Column(db.String(255), nullable=False)
    transcription = db.Column(db.Text)
    language = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())


class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(255),
                      nullable=False)
    author = db.Column(db.String(255),
                       nullable=True)
    total_tokens = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
    chunks = db.relationship('DocumentChunk', back_populates='document',
                             order_by='DocumentChunk.chunk_index',
                             cascade='all, delete, delete-orphan')  # Include "delete"


class DocumentChunk(db.Model):
    __tablename__ = 'document_chunks'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer,
                            db.ForeignKey('documents.id', ondelete='CASCADE'),
                            nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    tokens = db.Column(db.Integer, nullable=False)
    document = db.relationship('Document', back_populates='chunks')
    embeddings = db.relationship('DocumentEmbedding', back_populates='chunk',
                                 cascade='all, delete, delete-orphan')  # Add cascade option here
    __table_args__ = (
        db.Index('ix_document_chunks_document_id_chunk_index', 'document_id',
                 'chunk_index'),
    )


class DocumentEmbedding(db.Model):
    __tablename__ = 'document_embeddings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'))  # Add user_id for direct reference
    chunk_id = db.Column(db.Integer,
                         db.ForeignKey('document_chunks.id', ondelete='CASCADE'),
                         nullable=False)
    embedding = db.Column(db.LargeBinary,
                          nullable=False)  # The binary representation of the embedding
    model = db.Column(db.String(50),
                      nullable=False)  # The name of the model used to generate the embedding
    created_at = db.Column(db.DateTime(timezone=False),
                           server_default=func.now())  # Timestamp of when the embedding was created
    chunk = db.relationship('DocumentChunk', back_populates='embeddings')


class Translation(db.Model):
    __tablename__ = 'translations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    source_text = db.Column(db.Text, nullable=False)
    translated_text = db.Column(db.Text, nullable=False)
    source_language = db.Column(db.String(10), nullable=False)
    target_language = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())


class APIUsage(db.Model):
    __tablename__ = 'api_usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    endpoint = db.Column(db.String(50), nullable=False)
    request_payload = db.Column(db.Text)
    response_payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())


class Speech(db.Model):
    __tablename__ = 'speeches'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    text = db.Column(db.Text, nullable=False)
    voice = db.Column(db.String(50), nullable=False)
    audio_data = db.Column(db.Text,
                           nullable=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())


class GeneratedImage(db.Model):
    __tablename__ = 'generated_images'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
    uuid = db.Column(db.String(255), nullable=False, unique=True)

    user = db.relationship('User', back_populates='generated_images')
