import re
from datetime import timedelta, datetime
from app import db, User
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user

from app.database import UserAPIKey
from app.util.forms_util import ChangeUsernameForm, UploadAPIKeyForm, DeleteAPIKeyForm, \
    RetestAPIKeyForm, SelectAPIKeyForm
from app.util.session_util import check_available_models, test_gpt4, test_dalle3_key, \
    test_gpt3, encrypt_api_key, decrypt_api_key, hash_api_key

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/dashboard')
@login_required
def dashboard():
    user_api_keys = UserAPIKey.query.filter_by(user_id=current_user.id) \
        .filter(UserAPIKey.label != 'Error').all()
    selected_api_key_id = current_user.selected_api_key_id
    return render_template('dashboard.html', user_api_keys=user_api_keys,
                           selected_api_key_id=selected_api_key_id)


@bp.route('/change_username', methods=['POST'])
@login_required
def change_username():
    form = ChangeUsernameForm()
    if form.validate_on_submit():
        new_username = request.form.get('new_username').strip()

    if current_user.last_username_change and \
            datetime.utcnow() - current_user.last_username_change < timedelta(days=7):
        return jsonify({'status': 'error',
                        'message': 'You can only change your username once every 7 days.'}), 429

    if User.query.filter_by(username=new_username).first():
        return jsonify(
            {'status': 'error', 'message': 'This username is already taken.'}), 400

    current_user.username = new_username
    current_user.last_username_change = datetime.utcnow()
    db.session.commit()
    return jsonify(
        {'status': 'success', 'message': 'Your username has been updated.'}), 200


@bp.route('/upload_api_key', methods=['POST'])
@login_required
def upload_api_key():
    form = UploadAPIKeyForm()
    if form.validate_on_submit():
        api_key = request.form.get('api_key').strip()
        nickname = request.form.get('nickname')
    api_key_pattern = re.compile(r'sk-[A-Za-z0-9]{48}')
    if not api_key_pattern.match(api_key):
        return jsonify({'status': 'error', 'message': 'Invalid API key format.'}), 400

    api_key_token = hash_api_key(api_key)

    existing_key = UserAPIKey.query.filter_by(user_id=current_user.id,
                                              api_key_token=api_key_token).first()
    if existing_key:
        return jsonify({'status': 'error', 'message': 'API key already exists.'}), 400
    try:
        available_models = check_available_models(api_key)
        has_gpt_3_5_turbo = 'gpt-3.5-turbo' in available_models
        has_gpt_4 = 'gpt-4' in available_models
        label = 'Error'
        if has_gpt_4 and test_gpt4(api_key):
            label = 'gpt-4'
        elif has_gpt_3_5_turbo and test_gpt3(api_key):
            label = 'gpt-3.5-turbo'
        api_key_identifier = api_key[:6]
        encrypted_api_key = encrypt_api_key(api_key)

        counter = 1
        original_nickname = nickname
        while UserAPIKey.query.filter_by(user_id=current_user.id,
                                         nickname=nickname).filter(
            UserAPIKey.label != 'Error').first():
            nickname = f"{original_nickname}({counter})"
            counter += 1

        new_key = UserAPIKey(user_id=current_user.id,
                             encrypted_api_key=encrypted_api_key, nickname=nickname,
                             identifier=api_key_identifier, api_key_token=api_key_token,
                             label=label)
        db.session.add(new_key)
        db.session.commit()
        if label == 'Error':
            return jsonify({'success': False,
                            'status': 'error',
                            'message': 'API key is not valid.'}), 400
        else:
            return jsonify({'success': True,
                            'status': 'success',
                            'message': f'API key "{nickname}" added successfully with access to: ' + label}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {'status': 'error', 'message': 'Failed to verify API key'}), 400


@bp.route('/retest_api_key', methods=['POST'])
@login_required
def retest_api_key():
    form = RetestAPIKeyForm()
    if form.validate_on_submit():
        key_id = form.key_id.data
        user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id,
                                                  id=key_id).first()
        if not user_api_key:
            return jsonify({'success': False, 'message': 'API key not found'}), 404

        api_key = decrypt_api_key(user_api_key.encrypted_api_key)
        nickname = user_api_key.nickname
        try:
            available_models = check_available_models(api_key)
            has_gpt_3_5_turbo = 'gpt-3.5-turbo' in available_models
            has_gpt_4 = 'gpt-4' in available_models
            label = 'Error'
            if has_gpt_4 and test_gpt4(api_key):
                label = 'gpt-4'
            elif has_gpt_3_5_turbo and test_gpt3(api_key):
                label = 'gpt-3.5-turbo'
            user_api_key.label = label
            db.session.commit()
            if label == 'Error':
                return jsonify({'success': False, 'status': 'error',
                                'message': 'API key test failed, label set to Error'}), 400
            else:
                return jsonify({'success': True, 'status': 'success',
                                'message': f'API key "{nickname}" retested successfully with access to: ' + label}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'status': 'error',
                            'message': 'Failed to retest API key'}), 400
    else:
        return jsonify({'success': False, 'message': 'Invalid form submission.'}), 400


@bp.route('/delete_api_key', methods=['POST'])
@login_required
def delete_api_key():
    form = DeleteAPIKeyForm()
    if form.validate_on_submit():
        key_id = form.key_id.data
    user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id,
                                              id=key_id).first()
    if user_api_key:
        nickname = user_api_key.nickname
        db.session.delete(user_api_key)
        db.session.commit()
        return jsonify({'success': True, 'status': 'success',
                        'message': f'API key "{nickname}" deleted successfully'}), 200
    else:
        return jsonify({'success': False, 'status': 'error',
                        'message': 'Failed to delete API key'}), 400
    return redirect(url_for('user.dashboard'))


@bp.route('/select_api_key', methods=['POST'])
@login_required
def select_api_key():
    form = SelectAPIKeyForm()
    if form.validate_on_submit():
        key_id = request.form.get('key_id')
        user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id,
                                                  id=key_id).first()

        if not user_api_key:
            return jsonify({'success': False, 'message': 'API key not found'}), 404

        api_key = decrypt_api_key(user_api_key.encrypted_api_key)
        try:
            available_models = check_available_models(api_key)
            is_valid_key = 'gpt-3.5-turbo' in available_models or 'gpt-4' in available_models

            if not is_valid_key:
                return jsonify({'success': False, 'status': 'error',
                                'message': 'API key is not valid.'}), 400

            current_user.selected_api_key_id = user_api_key.id
            db.session.commit()
            return jsonify({'success': True, 'status': 'success',
                            'message': 'API key selected successfully.'}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'status': 'error',
                            'message': 'Failed to verify API key'}), 400
    else:
        return jsonify({'success': False, 'message': 'Invalid form submission.'}), 400
