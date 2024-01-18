import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

from config import ProductionConfig, DevelopmentConfig
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_login import LoginManager
from flask import Flask
from flask_assets import Environment
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.profiler import ProfilerMiddleware

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    flask_env = os.getenv("FLASK_ENV", "production").lower()
    if flask_env == "development":
        app.config.from_object(DevelopmentConfig)
        DevelopmentConfig.init_app(app)
    else:
        app.config.from_object(ProductionConfig)
        ProductionConfig.init_app(app)

    profile_env = os.getenv("FLASK_PROFILING", "false").lower()
    if profile_env == "true":
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[5])
    assets = Environment()

    CSRFProtect(app)
    CORS(app)
    db.init_app(app)
    Migrate(app, db)
    bcrypt.init_app(app)
    mail.init_app(app)
    assets.init_app(app)  # Initialize Flask-Assets

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    with app.app_context():
        from app.modules.user import user
        from app.modules.home import home
        from app.modules.image import image
        from app.modules.embedding import embedding
        from app.modules.chat import chat
        from app.modules.auth import auth
        from app.modules.audio import audio
        from .assets import compile_static_assets

        app.register_blueprint(home.home_bp)
        app.register_blueprint(auth.auth_bp)
        app.register_blueprint(user.user_bp)
        app.register_blueprint(image.image_bp)
        app.register_blueprint(embedding.embedding_bp)
        app.register_blueprint(chat.chat_bp)
        app.register_blueprint(audio.audio_bp)

        compile_static_assets(assets)

        @app.teardown_request
        def session_teardown(exception=None):
            if exception:
                db.session.rollback()
            db.session.remove()

        from app.models.session_models import after_update_listener
        from app.models.audio_models import TTSJob, TranscriptionJob, TranslationJob
        from app.models.chat_models import Conversation
        from app.models.image_models import GeneratedImage, MessageImages
        from app.models.user_models import UserAPIKey, User
        from app.models.embedding_models import Document

        db.create_all()
        for cls in [
            GeneratedImage,
            MessageImages,
            TTSJob,
            TranslationJob,
            TranscriptionJob,
            Conversation,
            UserAPIKey,
            User,
            Document,
        ]:
            event.listen(cls, "after_update", after_update_listener)

    return app
