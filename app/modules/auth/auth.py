import os
import re
from flask_login import login_user, logout_user, login_required, current_user
from markdown2 import markdown

from app.models.user_models import UserAPIKey, User
from app.utils.forms_util import LoginForm, SignupForm, ConfirmEmailForm, ResetPasswordRequestForm, ResetPasswordForm
from app.modules.auth.auth_util import decrypt_api_key, generate_confirmation_code
from flask import jsonify, Blueprint, request, render_template, redirect, url_for, flash, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask_mail import Message
from app import bcrypt, mail, login_manager, db
from sqlalchemy import or_
from datetime import datetime, timedelta

from app.utils.vector_cache import VectorCache

auth_bp = Blueprint("auth_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("user.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        login_credential = request.form.get("username")
        password = request.form.get("password")
        remember = request.form.get("remember") == "true"

        user = User.query.filter(or_(User.username == login_credential, User.email == login_credential)).first()

        if user is not None:
            if user.login_method in ["Github", "Google"]:
                message = f"Please use {user.login_method.title()} to sign in."
                return jsonify({"status": "oauth_login_required", "message": message})

            if user.login_attempts is None:
                user.login_attempts = 0

            time_since_last_attempt = datetime.utcnow() - (user.last_attempt_time or datetime(1970, 1, 1))

            if time_since_last_attempt > timedelta(minutes=5):
                user.login_attempts = 0
                user.last_attempt_time = None

            if user.login_attempts >= 3:
                return jsonify({"status": "error", "message": "Account locked. Please try again later."})

            if bcrypt.check_password_hash(user.password_hash, password):
                if user.email_confirmed:
                    user.login_attempts = 0
                    user.last_attempt_time = None
                    db.session.commit()
                    login_user(user, remember=remember)
                    return jsonify({"status": "success", "redirect": url_for("user.dashboard")})
                else:
                    return jsonify({"status": "unconfirmed", "redirect": url_for("auth.confirm_email")})
            else:
                user.login_attempts += 1
                user.last_attempt_time = datetime.utcnow()
                db.session.commit()
                remaining_attempts = 5 - user.login_attempts
                if user.login_attempts >= 5:
                    return jsonify(
                        {
                            "status": "error",
                            "message": "Invalid login credential or password. "
                            "Your account has been locked."
                            "Please try again in 5 minutes.",
                        }
                    )
                else:
                    return jsonify(
                        {
                            "status": "error",
                            "message": f"Invalid login credential or password. "
                            f"You have {remaining_attempts} more attempts.",
                        }
                    )

        return jsonify({"status": "error", "message": "Invalid login credential or password."})
    markdown_file_path = "static/home.md"

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template("login.html", form=form, tooltip=docs_content)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not email or not password:
            return (jsonify({"status": "error", "message": "All fields are required."}), 400)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return (jsonify({"status": "error", "message": "Invalid email address."}), 400)
        if (
            len(password) < 8
            or not re.search("[a-z]", password)
            or not re.search("[A-Z]", password)
            or not re.search("[0-9]", password)
        ):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Password must be at least 8 characters long "
                        "and include one number, one lowercase, "
                        "and one uppercase letter.",
                    }
                ),
                400,
            )
        if password != confirm_password:
            return (jsonify({"status": "error", "message": "Passwords do not match."}), 400)
        if User.query.filter_by(username=username).first():
            return (jsonify({"status": "error", "message": "Username already exists."}), 400)
        if User.query.filter_by(email=email).first():
            return (jsonify({"status": "error", "message": "Email already registered."}), 400)

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        confirmation_code = generate_confirmation_code()
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            email_confirmed=False,
            confirmation_code=confirmation_code,
            login_method="email",
        )
        db.session.add(new_user)
        db.session.commit()

        msg = Message("Confirm Your Email", sender=current_app.config["MAIL_DEFAULT_SENDER"], recipients=[email])
        msg.body = f"Your confirmation code is: {confirmation_code}"
        mail.send(msg)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "A a code has been sent to your email address.",
                    "redirect": url_for("auth.confirm_email"),
                }
            ),
            200,
        )
        markdown_file_path = os.path.join(current_app.root_path, auth_bp.static_folder, "auth.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template("signup.html", form=form, tooltip=docs_content)


@auth_bp.route("/confirm_email", methods=["GET", "POST"])
def confirm_email():
    form = ConfirmEmailForm()
    if form.validate_on_submit():
        code = request.form.get("code")
        user = User.query.filter_by(confirmation_code=code).first()
        if user:
            user.email_confirmed = True
            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "message": "Redirecting to login page in 5s...",
                    "redirect": url_for("auth.login"),
                }
            )
        else:
            return (jsonify({"status": "error", "message": "Invalid confirmation code."}), 400)
        markdown_file_path = os.path.join(current_app.root_path, auth_bp.static_folder, "auth.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template("confirm_email.html", form=form, tooltip=docs_content)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    VectorCache.clear_cache()
    return redirect(url_for(".login"))


@auth_bp.route("/get_api_keys", methods=["GET"])
def get_api_keys():
    user_api_keys = UserAPIKey.query.filter_by(user_id=current_user.id).all()
    decrypted_api_keys = [
        {"id": key.id, "api_key": decrypt_api_key(key.encrypted_api_key), "label": key.label} for key in user_api_keys
    ]
    return jsonify(decrypted_api_keys)


@auth_bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()

        if not user:
            return (jsonify({"status": "error", "message": "No account with that email address."}), 404)
        else:
            if user.login_method in ["Github", "Google"]:
                message = f"Please use {user.login_method.title()} to sign in."
                return jsonify({"status": "oauth_login_required", "message": message})

        token = s.dumps({"user_id": user.id}, salt="password-reset")
        user.reset_token_hash = bcrypt.generate_password_hash(token).decode("utf-8")
        db.session.commit()

        msg = Message("Password Reset Request", sender=current_app.config["MAIL_DEFAULT_SENDER"], recipients=[email])
        reset_link = url_for("auth.reset_password", token=token, _external=True)
        msg.body = f"Please click on the link to reset your password: {reset_link}. " f"It resets in 5 minutes."
        mail.send(msg)

        return (jsonify({"status": "success", "message": "An email has been sent with further instructions."}), 200)
        markdown_file_path = os.path.join(current_app.root_path, auth_bp.static_folder, "auth.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template("reset_password.html", form=form, tooltip=docs_content)


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    form = ResetPasswordForm()
    try:
        token_data = s.loads(token, salt="password-reset", max_age=300)
        user_id = token_data["user_id"]
        user = User.query.get(user_id)

        if not bcrypt.check_password_hash(user.reset_token_hash, token):
            flash("Invalid or stale token. Please request another", "token")
            return redirect(url_for("auth.reset_password_request"))

    except (ValueError, BadSignature):
        flash("Invalid or stale token. Please request another", "token")
        return redirect(url_for("auth.reset_password_request"))

    if form.validate_on_submit():
        password = form.password.data
        confirm_password = form.confirm_password.data

        if password != confirm_password:
            return (jsonify({"status": "error", "message": "Passwords do not match."}), 400)

        if (
            len(password) < 8
            or not re.search("[a-z]", password)
            or not re.search("[A-Z]", password)
            or not re.search("[0-9]", password)
        ):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Password must be at least 8 characters long and "
                        "include one number, "
                        "one lowercase, "
                        "and one uppercase letter.",
                    }
                ),
                400,
            )

        user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user.reset_token_hash = 0
        db.session.commit()
        return (
            jsonify(
                {"status": "success", "message": "Your password has been updated!", "redirect": url_for("auth.login")}
            ),
            200,
        )

    if form.errors:
        return jsonify({"status": "error", "errors": form.errors}), 400
        markdown_file_path = os.path.join(current_app.root_path, auth_bp.static_folder, "auth.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    return render_template("reset_password.html", form=form, token=token, tooltip=docs_content)
