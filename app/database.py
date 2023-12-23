import uuid
from flask_login import UserMixin
from sqlalchemy import BLOB
from sqlalchemy.sql import func
from app import db


def generate_default_nickname():
    max_number = db.session.query(db.func.max(UserAPIKey.nickname)).scalar()
    next_number = int(max_number or 0) + 1  # Increment the max number by 1
    return f"User{next_number}"


class UserAPIKey(db.Model):
    __tablename__ = 'user_api_keys'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    nickname = db.Column(db.String(25), nullable=False,
                         default=generate_default_nickname)
    identifier = db.Column(db.String(6), nullable=False)
    encrypted_api_key = db.Column(BLOB, nullable=False)
    label = db.Column(db.String(50))
    api_key_token = db.Column(db.String(64), unique=True, nullable=False,
                              default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
    usage_image_gen = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_chat = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_embedding = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_audio = db.Column(db.Numeric(10, 5), default=0, nullable=False)


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

    selected_api_key_id = db.Column(db.Integer, db.ForeignKey('user_api_keys.id',
                                                              ondelete='CASCADE'),
                                    nullable=True)

    conversations = db.relationship('Conversation', backref='user', lazy='dynamic')
    document_embeddings = db.relationship('DocumentEmbedding', backref='user',
                                          lazy='dynamic')
    documents = db.relationship('Document', backref='user', lazy='dynamic')
    api_usage = db.relationship('APIUsage', backref='user', lazy='dynamic')
    api_keys = db.relationship('UserAPIKey', backref='user', lazy='dynamic',
                               foreign_keys=[UserAPIKey.user_id])
    selected_api_key = db.relationship('UserAPIKey', foreign_keys=[selected_api_key_id]
                                       )
    generated_images = db.relationship('GeneratedImage', back_populates='user',
                                       lazy='dynamic')
    chat_preferences = db.relationship('ChatPreferences', backref='user', uselist=False,
                                       cascade='all, delete-orphan')


class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=True, default='New Conversation')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
    system_prompt = db.Column(db.String(2048),
                              nullable=True)  # New field for system prompts
    last_checked_time = db.Column(
        db.DateTime(timezone=False))  # New field for last checked time
    is_interrupted = db.Column(db.Boolean, default=False)

    messages = db.relationship('Message', backref='conversation', lazy='dynamic',
                               cascade='all, delete-orphan')


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer,
                                db.ForeignKey('conversations.id', ondelete='CASCADE'))
    content = db.Column(db.Text, nullable=False)
    direction = db.Column(db.Enum('incoming', 'outgoing'), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    is_knowledge_query = db.Column(db.Boolean, default=False)
    is_voice = db.Column(db.Boolean, default=False)
    is_vision = db.Column(db.Boolean, default=False)
    is_error = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
    message_images = db.relationship('MessageImages', backref='message', lazy='joined',
                                     cascade='all, delete-orphan')


class ChatPreferences(db.Model):
    __tablename__ = 'chat_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    model = db.Column(db.String(50), default='gpt-3.5-turbo')
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=2000)
    frequency_penalty = db.Column(db.Float, default=0.0)
    presence_penalty = db.Column(db.Float, default=0.0)
    top_p = db.Column(db.Float, default=1.0)
    stream = db.Column(db.Boolean, default=True)
    voice_mode = db.Column(db.Boolean, default=False)
    voice_model = db.Column(db.String(50), default='alloy')
    vision_mode = db.Column(db.Boolean, default=False)
    knowledge_query_mode = db.Column(db.Boolean, default=False)


class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'))
    title = db.Column(db.String(255),
                      nullable=False)
    author = db.Column(db.String(255),
                       nullable=True)
    total_tokens = db.Column(db.Integer, nullable=False)
    pages = db.Column(db.String(25), nullable=True)
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
    pages = db.Column(db.Integer, nullable=True)
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
                        db.ForeignKey('users.id',
                                      ondelete='CASCADE'))  # Add user_id for direct reference
    chunk_id = db.Column(db.Integer,
                         db.ForeignKey('document_chunks.id', ondelete='CASCADE'),
                         nullable=False)
    embedding = db.Column(db.LargeBinary,
                          nullable=False)
    model = db.Column(db.String(50),
                      nullable=False)
    created_at = db.Column(db.DateTime(timezone=False),
                           server_default=func.now())  # Timestamp of when the embedding was created
    chunk = db.relationship('DocumentChunk', back_populates='embeddings')


class APIUsage(db.Model):
    __tablename__ = 'api_usage'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    usage_image_gen = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_chat = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_embedding = db.Column(db.Numeric(10, 5), default=0, nullable=False)
    usage_audio = db.Column(db.Numeric(10, 5), default=0, nullable=False)


class GeneratedImage(db.Model):
    __tablename__ = 'generated_images'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime(timezone=False), server_default=func.now())
    uuid = db.Column(db.String(255), nullable=False, unique=True)

    user = db.relationship('User', back_populates='generated_images')


class MessageImages(db.Model):
    __tablename__ = 'message_images'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(255), nullable=False, unique=True)
    image_url = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    conversation_id = db.Column(db.Integer,
                                db.ForeignKey('conversations.id', ondelete='CASCADE'))
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='CASCADE'),
                           nullable=True)
    user = db.relationship('User', backref='message_images', lazy='joined')
    conversation = db.relationship('Conversation', backref='message_images',
                                   lazy='joined')
