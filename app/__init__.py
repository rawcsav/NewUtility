from app import config
import cloudinary
import sshtunnel
from flask import Flask
from flask_migrate import Migrate
from app.database import db
from app.util.session_util import get_tunnel
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_login import LoginManager

bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.secret_key = config.SECRET_KEY

    app.config[
        'SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQL_ALCHEMY_TRACK_MODIFICATIONS
    app.config['SQLALCHEMY_ECHO'] = config.SQLALCHEMY_ECHO
    app.config["SESSION_PERMANENT"] = config.SESSION_PERMANENT
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME

    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE
    app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'pool_reset_on_return': 'rollback'
    }

    app.config['MAIL_SERVER'] = config.MAIL_SERVER
    app.config['MAIL_PORT'] = config.MAIL_PORT
    app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
    app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
    app.config['MAIL_USE_SSL'] = config.MAIL_USE_SSL

    if config.FLASK_ENV == 'development':
        sshtunnel.SSH_TIMEOUT = 5.0
        sshtunnel.TUNNEL_TIMEOUT = 5.0
        app.tunnel = get_tunnel()
        app.config[
            'SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{config.SQL_USERNAME}:{config.SQL_PASSWORD}@127.0.0.1:{app.tunnel.local_bind_port}/{config.SQL_DB_NAME}'
        app.config["SESSION_COOKIE_SECURE"] = False

        cloudinary.config(
            cloud_name=config.CLOUD_NAME,
            api_key=config.CLOUD_API_KEY,
            api_secret=config.CLOUD_SECRET,
        )
    else:
        app.tunnel = None
        app.config[
            'SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{config.SQL_USERNAME}:{config.SQL_PASSWORD}@{config.SQL_HOSTNAME}/{config.SQL_DB_NAME}'
        app.config["SESSION_COOKIE_SECURE"] = True

        cloudinary.config(
            cloud_name=config.CLOUD_NAME,
            api_key=config.CLOUD_API_KEY,
            api_secret=config.CLOUD_SECRET,
            api_proxy="http://proxy.server:3128"
        )

    db.init_app(app)
    migrate = Migrate(app, db)

    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from .routes import auth
        app.register_blueprint(auth.bp)

        @app.teardown_request
        def session_teardown(exception=None):
            if exception:
                db.session.rollback()
            db.session.remove()

        db.create_all()

    return app
