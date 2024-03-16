import os
import ssl
from datetime import timedelta
import cloudinary
from urllib.parse import quote_plus

basedir = os.path.abspath(os.path.dirname(__file__))
appdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "app"))


class Config(object):
    FLASK_ENV = os.getenv("FLASK_ENV")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    ASSETS_DEBUG = False
    ASSETS_AUTO_BUILD = True

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_POOL_RECYCLE = 299
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 299,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "pool_reset_on_return": "rollback",
    }

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    SQL_HOSTNAME = os.getenv("SQL_HOSTNAME")
    SQL_USERNAME = os.getenv("SQL_USERNAME")
    SQL_PASSWORD = quote_plus(os.getenv("SQL_PASSWORD"))  # URL-encode the password
    SQL_DB_NAME = os.getenv("SQL_DB_NAME")

    SSH_HOST = os.getenv("SSH_HOST")
    SSH_USER = os.getenv("SSH_USER")
    SSH_PASS = os.getenv("SSH_PASS")

    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_USERNAME")

    CLOUD_NAME = os.getenv("CLOUD_NAME")
    CLOUD_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUD_SECRET = os.getenv("CLOUDINARY_SECRET")

    GOOGLE_SITE_KEY = os.getenv("GOOGLE_SITE_KEY")
    GOOGLE_SECRET_KEY = os.getenv("GOOGLE_SECRET_KEY")
    GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_CALLBACK_URI = os.getenv("GOOGLE_CALLBACK_URI")

    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    GITHUB_CALLBACK_URI = os.getenv("GITHUB_CALLBACK_URI")

    DEFAULT_USER_PASSWORD = os.getenv("DEFAULT_USER_PASSWORD")

    @classmethod
    def init_app(cls, app):
        cloudinary.config(cloud_name=cls.CLOUD_NAME, api_key=cls.CLOUD_API_KEY, api_secret=cls.CLOUD_SECRET)


class DevelopmentConfig(Config):
    FLASK_DEBUG = True
    ASSETS_DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

    @classmethod
    def init_app(cls, app):
        super().init_app(app)  # Call the parent init_app
        app.tunnel = None
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            f"mysql+pymysql://{os.getenv('SQL_USERNAME')}:"
            f"{quote_plus(os.getenv('SQL_PASSWORD'))}@{os.getenv('SQL_HOSTNAME')}:"
            f"3306/{os.getenv('SQL_DB_NAME')}"
        )


class ProductionConfig(Config):
    FLASK_DEBUG = False
    ASSETS_DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def init_app(cls, app):
        super().init_app(app)  # Call the parent init_app
        app.tunnel = None
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            f"mysql+pymysql://{os.getenv('SQL_USERNAME')}:"
            f"{quote_plus(os.getenv('SQL_PASSWORD'))}@{os.getenv('SQL_HOSTNAME')}:"
            f"3306/{os.getenv('SQL_DB_NAME')}"
        )
