import re

import requests
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from app.database import db, UserAPIKey, User
from app.util.session_util import encrypt_api_key, decrypt_api_key, \
    generate_confirmation_code, random_string, verify_recaptcha, get_or_create_user
from flask import jsonify, Blueprint, request, render_template, redirect, url_for, \
    flash, session
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
from app import bcrypt, mail, config, login_manager, oauth
from sqlalchemy import or_
from datetime import datetime, timedelta

bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_credential = request.form.get('username')
        password = request.form.get('password')
        recaptcha_response = request.form.get('g-recaptcha-response')
        recaptcha_error = verify_recaptcha(recaptcha_response)
        if recaptcha_error:
            return jsonify(*recaptcha_error)

        user = User.query.filter(
            or_(User.username == login_credential, User.email == login_credential)
        ).first()

        if user is not None:
            if user.login_attempts is None:
                user.login_attempts = 0
            if user.last_attempt_time and datetime.utcnow() - user.last_attempt_time < timedelta(
                    minutes=5) and user.login_attempts >= 3:
                return jsonify({'status': 'error',
                                'message': 'Account locked. Please try again later.'})

            if bcrypt.check_password_hash(user.password_hash, password):
                if user.email_confirmed:
                    user.login_attempts = 0
                    user.last_attempt_time = None
                    db.session.commit()
                    login_user(user)
                    return jsonify(
                        {'status': 'success', 'redirect': url_for('user.dashboard')})
                else:
                    return jsonify({'status': 'unconfirmed',
                                    'redirect': url_for('auth.confirm_email')})
            else:
                user.login_attempts += 1
                user.last_attempt_time = datetime.utcnow()
                db.session.commit()
                if user.login_attempts >= 3:

                    return jsonify({'status': 'error',
                                    'message': 'Invalid login credential or password. Your account has been locked due to too many failed login attempts. Please try again in 5 minutes.'})
                else:
                    return jsonify({'status': 'error',
                                    'message': 'Invalid login credential or password.'})

        return jsonify(
            {'status': 'error', 'message': 'Invalid login credential or password.'})

    return render_template('login.html')


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        recaptcha_response = request.form.get('g-recaptcha-response')
        recaptcha_error = verify_recaptcha(recaptcha_response)
        if recaptcha_error:
            return jsonify(*recaptcha_error)

        if not username or not email or not password:
            return jsonify(
                {'status': 'error', 'message': 'All fields are required.'}), 400
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify(
                {'status': 'error', 'message': 'Invalid email address.'}), 400
        if len(password) < 8 or not re.search("[a-z]", password) or not re.search(
                "[A-Z]", password) or not re.search("[0-9]", password):
            return jsonify({
                'status': 'error',
                'message': 'Password must be at least 8 characters long and include one number, one lowercase, and one uppercase letter.'
            }), 400
        if password != confirm_password:
            return jsonify(
                {'status': 'error', 'message': 'Passwords do not match.'}), 400
        if User.query.filter_by(username=username).first():
            return jsonify(
                {'status': 'error', 'message': 'Username already exists.'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify(
                {'status': 'error', 'message': 'Email already registered.'}), 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        confirmation_code = generate_confirmation_code()
        new_user = User(username=username, email=email, password_hash=hashed_password,
                        email_confirmed=False, confirmation_code=confirmation_code)
        db.session.add(new_user)
        db.session.commit()

        msg = Message('Confirm Your Email', sender=config.MAIL_DEFAULT_SENDER,
                      recipients=[email])
        msg.body = f'Your confirmation code is: {confirmation_code}'
        mail.send(msg)

        return jsonify({
            'status': 'success',
            'message': 'A confirmation email with a code has been sent to your email address.',
            'redirect': url_for('auth.confirm_email')
        }), 200

    return render_template('signup.html')


@bp.route('/confirm_email', methods=['GET', 'POST'])
def confirm_email():
    if request.method == 'POST':
        code = request.form.get('code')

        user = User.query.filter_by(confirmation_code=code).first()
        if user:
            user.email_confirmed = True
            db.session.commit()
            flash('Email confirmed successfully!', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid confirmation code.', 'danger')

    return render_template('confirm_email.html')


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


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    s = URLSafeTimedSerializer(config.SECRET_KEY)
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
    # Pass an empty token to use the same template for requesting a reset
    return render_template('reset_password.html', token=None)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = URLSafeTimedSerializer(config.SECRET_KEY)
    try:
        email = s.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('The password reset link is expired.', 'warning')
        return redirect(url_for('auth.reset_password_request'))
    except BadSignature:
        flash('Invalid or expired token.', 'warning')
        return redirect(url_for('auth.reset_password_request'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid user.', 'warning')
        return redirect(url_for('auth.reset_password_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        if len(password) < 8 or not re.search("[a-z]", password) or \
                not re.search("[A-Z]", password) or not re.search("[0-9]", password):
            flash(
                'Password must be at least 8 characters long and include one number, one lowercase, and one uppercase letter.',
                'danger'
            )
            return redirect(url_for('auth.reset_password', token=token))

        user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        db.session.commit()
        flash('Your password has been updated!', 'success')
        login_user(user, remember=True)
        return redirect(url_for('user.dashboard'))

    return render_template('reset_password.html', token=token)


@bp.route('/login/google')
def google_login():
    redirect_uri = config.GOOGLE_CALLBACK_URI
    print(redirect_uri)
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route('/login/github')
def github_login():
    redirect_uri = config.GITHUB_CALLBACK_URI
    return oauth.github.authorize_redirect(redirect_uri)


@bp.route('/login/google/authorized')
def google_authorized():
    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        flash('Access denied or login canceled by the user.', 'error')
        return redirect(url_for('.login'))

    resp = oauth.google.get('userinfo')
    if resp.status_code != 200:
        flash('Failed to fetch user information from Google.', 'error')
        return redirect(url_for('.login'))

    user_info = resp.json()
    email = user_info['email']
    original_username = user_info.get('name', email.split('@')[0])
    user = get_or_create_user(email, original_username, 'Google')

    login_user(user, remember=True)
    flash('You have been successfully logged in via Google.', 'success')
    return redirect(url_for('user.dashboard'))


@bp.route('/login/github/authorized')
def github_authorized():
    try:
        token = oauth.github.authorize_access_token()
    except Exception as e:
        flash('Failed to authenticate with GitHub.', 'error')
        return redirect(url_for('.login'))

    resp = oauth.github.get('user')
    if resp.status_code != 200:
        flash('Failed to fetch user data from GitHub.', 'error')
        return redirect(url_for('.login'))

    user_data = resp.json()
    email = user_data.get('email')  # Some GitHub users may have private emails
    original_username = user_data['login']
    user = get_or_create_user(email, original_username, 'GitHub')

    login_user(user, remember=True)
    flash('You have been successfully logged in via GitHub.', 'success')
    return redirect(url_for('user.dashboard'))
