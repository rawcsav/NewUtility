import os
from flask_sqlalchemy import SQLAlchemy
from app.config import Config, ProductionConfig, DevelopmentConfig
from authlib.integrations.flask_client import OAuth
from flask_migrate import Migrate
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_login import LoginManager
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.profiler import ProfilerMiddleware

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
oauth = OAuth()


def create_app():
    app = Flask(__name__)
    flask_env = os.getenv("FLASK_ENV", "production").lower()
    if flask_env == "development":
        app.config.from_object(DevelopmentConfig)
        DevelopmentConfig.init_app(oauth, app)
    else:
        app.config.from_object(ProductionConfig)
        ProductionConfig.init_app(oauth, app)

    profile_env = os.getenv("FLASK_PROFILING", "false").lower()
    if profile_env == "true":
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[5], )

    CSRFProtect(app)
    CORS(app)
    db.init_app(app)
    Migrate(app, db)
    bcrypt.init_app(app)
    mail.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    with app.app_context():
        from .routes import landing, auth, user, image, embed, chat

        app.register_blueprint(landing.bp)
        app.register_blueprint(auth.bp)
        app.register_blueprint(user.bp)
        app.register_blueprint(image.bp)
        app.register_blueprint(embed.bp)
        app.register_blueprint(chat.bp)

        @app.teardown_request
        def session_teardown(exception=None):
            if exception:
                db.session.rollback()
            db.session.remove()

        db.create_all()

    return app
