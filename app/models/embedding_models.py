from sqlalchemy.orm import backref

from app import db
from app.models.mixins import generate_uuid, SoftDeleteMixin, TimestampMixin


class ModelContextWindow(db.Model):
    __tablename__ = "model_context_windows"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    model_name = db.Column(db.String(50), nullable=False, unique=True)
    context_window_size = db.Column(db.Integer, nullable=False)


class Document(db.Model, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "documents"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True)
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
        primaryjoin="and_(Document.id==DocumentChunk.document_id, Document.delete==False)",
    )


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    document_id = db.Column(
        db.String(36), db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
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
    __table_args__ = (db.Index("ix_document_chunks_document_id_chunk_index", "document_id", "chunk_index"),)


class DocumentEmbedding(db.Model, TimestampMixin):
    __tablename__ = "document_embeddings"
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    chunk_id = db.Column(
        db.String(36), db.ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, unique=True
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
        backref=backref("embeddings", cascade="all, delete-orphan"),
    )
