from flask import Flask, request, jsonify, Blueprint, render_template
import openai
import os
from flask_login import login_required, current_user

from app.database import GeneratedImage, db, UserAPIKey, User
from app.util.forms_util import GenerateImageForm
from app.util.session_util import decrypt_api_key

bp = Blueprint('image', __name__, url_prefix='/image')


@bp.route('/generate_image', methods=['GET', 'POST'])
@login_required
def generate_image():
    form = GenerateImageForm()
    image_urls = []
    error_message = None

    if form.validate_on_submit():
        try:
            prompt = form.prompt.data
            model = form.model.data or 'dall-e-2'
            n = form.n.data or 1
            size = form.size.data or '1024x1024'

            key_id = current_user.selected_api_key_id
            user_api_key = UserAPIKey.query.filter_by(user_id=current_user.id,
                                                      id=key_id).first()
            api_key = decrypt_api_key(user_api_key.encrypted_api_key)

            openai.api_key = api_key

            request_params = {
                'model': model,
                'prompt': prompt,
                'n': n,
                'size': size
            }

            if model.startswith('dall-e-3'):
                quality = form.quality.data
                style = form.style.data

                if quality:
                    request_params['quality'] = quality
                if style:
                    request_params['style'] = style

            response = openai.images.generate(**request_params)

            # Directly access the 'data' attribute of the response
            for image_response in response.data:
                # Access the 'url' attribute of each image object
                image_url = image_response.url
                image_urls.append(image_url)
                new_image = GeneratedImage(
                    user_id=current_user.id,
                    prompt=prompt,
                    model=model,
                    image_url=image_url,
                )
                db.session.add(new_image)
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'image_urls': image_urls,
                    'error_message': error_message,
                    'status': 'success'  # or 'error' based on your logic
                })
        except Exception as e:
            error_message = str(e)
            print(f"Error generating image: {error_message}")  # Log the error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # The request is an AJAX request, return a JSON response for the error
                return jsonify({
                    'error_message': error_message,
                    'status': 'error'
                })
            # For a regular request, you might want to render the page with the error message
            return render_template(
                'image.html',
                form=form,
                image_urls=image_urls,
                error_message=error_message
            )

    return render_template(
        'image.html',
        form=form,
        image_urls=image_urls,
        error_message=error_message
    )
