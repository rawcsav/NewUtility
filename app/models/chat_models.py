from app import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, generate_uuid


class MessageChunkAssociation(db.Model):
    __tablename__ = "message_chunk_association"

    message_id = db.Column(db.String(36), db.ForeignKey("messages.id"), primary_key=True)
    chunk_id = db.Column(db.String(36), db.ForeignKey("document_chunks.id", ondelete="CASCADE"), primary_key=True)
    similarity_rank = db.Column(db.Integer, nullable=False)  # Store the ranking here

    message = db.relationship("Message", back_populates="chunk_associations")
    chunk = db.relationship("DocumentChunk", back_populates="message_associations")


class Conversation(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "conversations"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(255), nullable=True, default="New Conversation")
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True)
    system_prompt = db.Column(db.String(2048), nullable=True)  # New field for system prompts
    last_checked_time = db.Column(db.DateTime(timezone=False))
    is_interrupted = db.Column(db.Boolean, default=False)
    messages = db.relationship(
        "Message",
        primaryjoin="and_(Conversation.id==Message.conversation_id, Message.delete==False)",
        backref="conversation",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class Message(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "messages"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
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
        cascade="all, delete-orphan",
    )
    chunk_associations = db.relationship(
        "MessageChunkAssociation", back_populates="message", cascade="all, delete-orphan"
    )


class ChatPreferences(db.Model):
    __tablename__ = "chat_preferences"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    model = db.Column(db.String(50), default="gpt-3.5-turbo")
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=2000)
    frequency_penalty = db.Column(db.Float, default=0.0)
    presence_penalty = db.Column(db.Float, default=0.0)
    top_p = db.Column(db.Float, default=1.0)
    voice_mode = db.Column(db.Boolean, default=False)
    voice_model = db.Column(db.String(50), default="alloy")
    knowledge_query_mode = db.Column(db.Boolean, default=False)
    top_k = db.Column(db.Integer, default=5)
    threshold = db.Column(db.Float, default=0.5)
    cwd_system_prompt = db.Column(db.String(2048),
                                  nullable=True,
                                  default="You are a helpful academic literary assistant. "
                                          "Provide in -depth guidance, suggestions, code snippets, "
                                          "and explanations as needed to help the user. "
                                          "Leverage your expertise and intuition to offer innovative and effective solutions. "
                                          "Be informative, clear, and concise in your responses, and focus on providing accurate and reliable information. "
                                          "Use the provided text excerpts directly to aid in your responses."
                                  )  # New field for system prompts
