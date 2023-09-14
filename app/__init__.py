import os
from datetime import datetime

from flask import Flask, session, current_app
from flask_session import Session

from app import config
from app.util.docauth_util import remove_directory


def create_app():
    app = Flask(__name__)

    app.secret_key = config.SECRET_KEY
    app.config['SESSION_TYPE'] = config.SESSION_TYPE
    app.config['SESSION_PERMANENT'] = config.SESSION_PERMANENT
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME
    Session(app)

    app.app_context().push()

    @app.before_request
    def before_request():
        session.modified = True  # ensure every request resets the session lifetime

        if 'last_activity' in session:
            elapsed = datetime.utcnow() - session['last_activity']
            session_lifetime = current_app.config.get('PERMANENT_SESSION_LIFETIME')
            if elapsed > session_lifetime:
                # This session is expired, clean up the resources
                main_upload_dir = session.get('UPLOAD_DIR')
                remove_directory(main_upload_dir)
                session.clear()  # Clear session data

        session['last_activity'] = datetime.utcnow()
        # Ensure UPLOAD_DIR exists
        if 'UPLOAD_DIR' not in session:
            session_id = str(id(session))
            session_dir = os.path.join(config.MAIN_TEMP_DIR, session_id)
            os.makedirs(session_dir, exist_ok=True)
            session['UPLOAD_DIR'] = session_dir

        # Ensure CHAT_UPLOAD_DIR exists
        if 'CHAT_UPLOAD_DIR' not in session:
            chat_dir = os.path.join(session['UPLOAD_DIR'], 'chatwithdocs')
            os.makedirs(chat_dir, exist_ok=True)
            session['CHAT_UPLOAD_DIR'] = chat_dir

        # Ensure EMBED_DATA exists
        if 'EMBED_DATA' not in session:
            EMBED_DATA_PATH = os.path.join(session['CHAT_UPLOAD_DIR'], 'embed_data.json')
            session['EMBED_DATA'] = EMBED_DATA_PATH
            if not os.path.exists(EMBED_DATA_PATH):
                with open(EMBED_DATA_PATH, 'w') as f:
                    pass

        # Ensure WHISPER_UPLOAD_DIR exists
        if 'WHISPER_UPLOAD_DIR' not in session:
            whisper_dir = os.path.join(session['UPLOAD_DIR'], 'whisper')
            os.makedirs(whisper_dir, exist_ok=True)
            session['WHISPER_UPLOAD_DIR'] = whisper_dir

    from .routes import auth, documents, query, whisper_main, whisper_errors, landing  # <- Add 'landing' here
    app.register_blueprint(auth.bp)
    app.register_blueprint(documents.bp)
    app.register_blueprint(query.bp)
    app.register_blueprint(whisper_main.bp)
    app.register_blueprint(whisper_errors.bp)
    app.register_blueprint(landing.bp)

    # scheduler = BackgroundScheduler()
    # scheduler.add_job(scheduled_cleanup, 'interval', hours=1)  # Run every hour
    # scheduler.start()

    return app
