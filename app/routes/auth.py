from flask import (
    Blueprint, request, redirect, url_for, flash,
    render_template, jsonify
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from app import bcrypt, mail, login_manager
from app.database import db, UserAPIKey, User
from app import config
from app.util.session_util import encrypt_api_key, decrypt_api_key
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_mail import Message

bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.json.get('username')
        password = request.json.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return jsonify({'status': 'success', 'redirect': url_for('user.dashboard')})
        else:
            return jsonify(
                {'status': 'error', 'message': 'Invalid username or password'}
            )
    else:
        return render_template('login.html')


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('.signup'))
        new_user = User(
            username=username,
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8')
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('.login'))
    return render_template('signup.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('.login'))


@bp.route('/add_api_key', methods=['POST'])
def add_api_key():
    api_key = request.form.get('api_key')
    label = request.form.get('label')
    encrypted_api_key = encrypt_api_key(api_key)
    user_api_key = UserAPIKey(
        user_id=current_user.id,
        encrypted_api_key=encrypted_api_key,
        label=label
    )
    db.session.add(user_api_key)
    db.session.commit()


@bp.route('/get_api_keys', methods=['GET'])
def get_api_keys():
    user_api_keys = UserAPIKey.query.filter_by(user_id=current_user.id).all()
    decrypted_api_keys = [
        {
            'id': key.id,
            'api_key': decrypt_api_key(key.encrypted_api_key),
            'label': key.label
        } for key in user_api_keys
    ]
    return jsonify(decrypted_api_keys)


s = URLSafeTimedSerializer(config.SECRET_KEY)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt='password-reset')
            msg = Message(
                'Password Reset Request',
                sender=config.MAIL_DEFAULT_SENDER,
                recipients=[email]
            )
            link = url_for('auth.reset_password', token=token, _external=True)
            msg.body = f'Your link to reset your password is {link}'
            mail.send(msg)
            flash(
                'An email has been sent with instructions to reset your password.',
                'info'
            )
        else:
            flash('No account with that email.', 'warning')
    return render_template('reset_password_request.html')


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('The password reset link is expired.', 'warning')
        return redirect(url_for('auth.reset_password_request'))
    except:  # catch other exceptions such as BadSignature
        flash('Invalid or expired token.', 'warning')
        return redirect(url_for('auth.reset_password_request'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid user.', 'warning')
        return redirect(url_for('auth.reset_password_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)
