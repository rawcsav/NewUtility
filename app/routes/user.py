import re
from datetime import timedelta, datetime

import openai

from app import db, User
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user

from app.database import UserAPIKey
from app.util.session_util import check_available_models, test_gpt4, test_dalle3_key, \
    test_gpt3

# Define the Blueprint
bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/dashboard')
@login_required  # Ensure that only logged-in users can access this route
def dashboard():
    return render_template('dashboard.html', user=current_user)


@bp.route('/change_username', methods=['POST'])
@login_required
def change_username():
    new_username = request.form.get('new_username').strip()
    # Check if the cooldown period has passed
    if current_user.last_username_change and \
            datetime.utcnow() - current_user.last_username_change < timedelta(days=7):
        return jsonify({'status': 'error',
                        'message': 'You can only change your username once every 7 days.'}), 429
    # Check if the new username is already taken
    if User.query.filter_by(username=new_username).first():
        return jsonify(
            {'status': 'error', 'message': 'This username is already taken.'}), 400
    # Update the username
    current_user.username = new_username
    current_user.last_username_change = datetime.utcnow()
    db.session.commit()
    return jsonify(
        {'status': 'success', 'message': 'Your username has been updated.'}), 200


@bp.route('/upload_api_keys', methods=['POST'])
def upload_api_keys():
    api_keys = []
    file = request.files.get('api_keys_file')
    text_input = request.form.get('api_keys_text')

    # Process file input if it exists
    if file and file.filename != '':
        api_key_pattern = re.compile(r'sk-[A-Za-z0-9]{48}')

        content = file.read().decode('utf-8')

        file_keys = api_key_pattern.findall(content)

        unique_api_keys = list(set(file_keys))
        api_keys.extend(unique_api_keys)

    # Process text area input using regex
    if text_input:
        api_keys.extend(re.findall(r'sk-\w{48}', text_input))

    if not api_keys:
        flash('No API keys provided')
        return redirect(request.url)
    new_keys = []
    for key in api_keys:
        # Check if the key is already in the database
        existing_key = UserAPIKey.query.filter_by(encrypted_api_key=key).first()
        if not existing_key:
            new_key = UserAPIKey(user_id=current_user.id, encrypted_api_key=key)
            new_keys.append(new_key)
            db.session.merge(new_key)

    db.session.commit()
    new_keys_count = len(new_keys)
    if new_keys_count > 0:
        return jsonify(success=True,
                       message=f'{new_keys_count} new API key(s) uploaded successfully')
    else:
        return jsonify(success=True, message='No new API keys were added')


@bp.route('/update_models', methods=['GET'])
@login_required
def update_models():
    user_api_keys = UserAPIKey.query.filter_by(user_id=current_user.id).all()
    total_keys = len(user_api_keys)
    batch_size = 50  # Define the size of each batch
    batch_count = 0  # Counter for the current batch
    special_value = "NO_MODELS_OR_ERROR"

    for index, user_key in enumerate(user_api_keys):
        if user_key.models is not None and special_value in user_key.models:
            continue  # Skip this key

        try:
            api_key = user_key.encrypted_api_key  # Assuming the key is ready to use
            available_models = check_available_models(api_key)
            target_models = {'gpt-3.5-turbo', 'gpt-4', 'dall-e-3'}
            models_to_add = target_models.intersection(available_models)

            if models_to_add:
                current_models = set(
                    user_key.models.split(',')) if user_key.models else set()
                new_models = current_models.union(models_to_add)
                user_key.models = ','.join(new_models)
            else:
                user_key.models = special_value

        except Exception as e:
            user_key.models = special_value
            # Add the user_key to the session (prepare to commit)
        db.session.add(user_key)

        # Commit the session after every batch_size entries
        if (index + 1) % batch_size == 0 or (index + 1) == total_keys:
            db.session.commit()  # Commit the current batch
            batch_count += 1
            # Optionally, update progress file here if needed

            # Update progress in a file
            progress = (index + 1) / total_keys * 100
            with open(f"/tmp/user_{current_user.id}_progress.txt", "w") as f:
                f.write(str(progress))

        # Final commit if there are any remaining uncommitted changes
    if (total_keys % batch_size) != 0:
        db.session.commit()

    return jsonify(success=True, message='API keys checked and database updated.')


@bp.route('/progress', methods=['GET'])
@login_required
def get_progress():
    try:
        with open(f"/tmp/user_{current_user.id}_progress.txt", "r") as f:
            progress = f.read()
        return jsonify(progress=progress)
    except FileNotFoundError:
        return jsonify(progress="Not started"), 404


@bp.route('/test_api_keys', methods=['GET'])
@login_required
def test_and_update_api_keys():
    special_value = "NO_MODELS_OR_ERROR"
    user_api_keys = UserAPIKey.query.filter_by(user_id=current_user.id).all()
    batch_size = 50  # Number of records to process before committing
    processed_count = 0  # Counter for records processed

    for user_key in user_api_keys:
        if user_key.models is not None and special_value in user_key.models:
            continue  # Skip this key

        key = user_key.encrypted_api_key
        user_key.label = user_key.label or ''

        # Skip if all models are already labeled
        if all(model in user_key.label for model in
               ['gpt-4', 'dall-e-3', 'gpt-3.5-turbo']):
            continue

        # Test for GPT-4 if not already labeled
        # Initialize a flag to indicate if a test has passed
        test_passed = False

        # Test for GPT-4 if not already labeled
        if 'gpt-4' not in user_key.label:
            try:
                test_gpt4(key)
                # If GPT-4 test passes, label the key for all three models
                user_key.label = 'gpt-4,dall-e-3,gpt-3.5-turbo'
                test_passed = True  # Set the flag to True since the test passed
            except Exception as e:
                print(f"GPT-4 test failed for key {key} with exception: {e}")

        # If GPT-4 test did not pass, proceed to test for DALL-E 3
        if not test_passed and 'dall-e-3' not in user_key.label:
            try:
                test_dalle3_key(key)
                # If DALL-E 3 test passes, label the key for DALL-E 3 and GPT-3.5-Turbo
                user_key.label = 'dall-e-3,gpt-3.5-turbo'
                test_passed = True  # Update the flag since the test passed
            except Exception as e:
                print(f"DALL-E 3 test failed for key {key} with exception: {e}")

        # If neither GPT-4 nor DALL-E 3 tests passed, proceed to test for GPT-3.5-Turbo
        if not test_passed and 'gpt-3.5-turbo' not in user_key.label:
            try:
                test_gpt3(key)
                # Label the key for GPT-3.5-Turbo
                user_key.label += ',gpt-3.5-turbo' if user_key.label else 'gpt-3.5-turbo'
            except Exception as e:
                print(f"GPT-3.5-Turbo test failed for key {key} with exception: {e}")

        db.session.add(user_key)
        processed_count += 1

        # Commit the session after every batch_size entries
        if processed_count % batch_size == 0:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error during batch commit: {e}")

    if processed_count % batch_size != 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error during final commit: {e}")
            return jsonify(success=False, message=str(e)), 500

    return jsonify(success=True, message="API keys tested and labels updated."), 200
