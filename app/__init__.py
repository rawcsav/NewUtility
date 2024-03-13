import os
import ssl

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from flask_socketio import SocketIO
from config import ProductionConfig, DevelopmentConfig
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from celery import Celery
from flask_login import LoginManager
from flask import Flask, redirect, url_for
from flask_assets import Environment
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.profiler import ProfilerMiddleware
from app.utils.socket_util import GlobalNamespace, EmbeddingNamespace, ImageNamespace, AudioNamespace

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
socketio = SocketIO()
login_manager = LoginManager()
celery = Celery(__name__)
celery.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])


# noinspection PyPropertyAccess
def make_celery(app):
    celery.conf.broker_url = app.config["CELERY_BROKER_URL"]
    celery.conf.result_backend = app.config["CELERY_RESULT_BACKEND"]
    celery.conf.broker_use_ssl = {"ca_certs": app.config["RABBITMQ_CA_CERT"], "cert_reqs": ssl.CERT_REQUIRED}

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    celery.conf.update(app.config)
    return celery


def create_app():
    app = Flask(__name__)
    flask_env = os.getenv("FLASK_ENV", "production").lower()
    if flask_env == "development":
        app.config.from_object(DevelopmentConfig)
        DevelopmentConfig.init_app(app)
    else:
        print(flask_env)
        app.config.from_object(ProductionConfig)
        ProductionConfig.init_app(app)

    profile_env = os.getenv("FLASK_PROFILING", "false").lower()
    if profile_env == "true":
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[5])

    assets = Environment()
    CSRFProtect(app)
    CORS(app)
    db.init_app(app)

    socketio.init_app(app, message_queue=app.config["CELERY_BROKER_URL"], cors_allowed_origins="*")
    socketio.on_namespace(GlobalNamespace("/global"))
    socketio.on_namespace(ImageNamespace("/image"))
    socketio.on_namespace(EmbeddingNamespace("/embedding"))
    socketio.on_namespace(AudioNamespace("/audio"))

    Migrate(app, db)
    bcrypt.init_app(app)
    mail.init_app(app)
    assets.init_app(app)  # Initialize Flask-Assets
    celery = make_celery(app)

    app.extensions["celery"] = celery  # Add Celery to Flask extensions
    app.app_context().push()

    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    login_manager.login_view = "auth_bp.login"
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
        from app.modules.cwd import cwd

        app.register_blueprint(home.home_bp)
        app.register_blueprint(auth.auth_bp)
        app.register_blueprint(user.user_bp)
        app.register_blueprint(image.image_bp)
        app.register_blueprint(embedding.embedding_bp)
        app.register_blueprint(chat.chat_bp)
        app.register_blueprint(audio.audio_bp)
        app.register_blueprint(cwd.cwd_bp)
        from .assets import compile_static_assets

        compile_static_assets(assets)

        @app.teardown_request
        def session_teardown(exception=None):
            if exception:
                db.session.rollback()
            db.session.remove()

        @app.route("/")
        def root():
            # Redirect the user from root to '/home'
            return redirect(url_for("home_bp.landing_page"))

        db.create_all()

        from app.models.task_models import after_update_listener
        from app.models.audio_models import TTSJob, TranscriptionJob, TranslationJob
        from app.models.chat_models import Conversation
        from app.models.image_models import GeneratedImage, MessageImages
        from app.models.user_models import UserAPIKey, User
        from app.models.embedding_models import Document

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
