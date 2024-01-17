from app import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, generate_uuid


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
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="CASCADE"))
    message_id = db.Column(db.String(36), db.ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True)
    user = db.relationship("User", backref="message_images", lazy="joined")
    conversation = db.relationship("Conversation", backref="message_images", lazy="joined")
