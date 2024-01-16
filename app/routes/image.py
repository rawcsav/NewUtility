import os
from datetime import datetime

from flask import (
    request,
    jsonify,
    Blueprint,
    render_template,
    send_file,
    url_for,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound
from markdown2 import markdown
from app import db
from app.database import GeneratedImage
from app.util.forms_util import GenerateImageForm
from app.util.image_util import (
    generate_images,
    save_image_to_db,
    download_and_store_image,
)
from app.util.session_util import initialize_openai_client

bp = Blueprint("image", __name__, url_prefix="/image")

date_format = "%b %d, %Y at %I:%M %p"


@bp.route("/generate_image", methods=["GET", "POST"])
@login_required
def generate_image():
    form = GenerateImageForm()
    image_urls = []
    image_metadata = []  # List to hold metadata for each image
    error_message = None
    markdown_file_path = os.path.join(
        current_app.root_path, "static", "docs", "image.md"
    )

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    if form.validate_on_submit():
        try:
            prompt = form.prompt.data
            model = form.model.data or "dall-e-3"
            n = form.n.data or 1
            size = form.size.data or "1024x1024"
            quality = form.quality.data if model.startswith("dall-e-3") else None
            style = form.style.data if model.startswith("dall-e-3") else None
            request_params = {
                "model": model,
                "prompt": prompt,
                "n": n,
                "size": size,
                "quality": quality,
                "style": style,
            }

            client, error = initialize_openai_client(current_user.id)
            image_data = generate_images(
                client,
                request_params,
                current_user.id,
                current_user.selected_api_key_id,
            )

            download_dir = current_app.config["USER_IMAGE_DIRECTORY"]
            for image_response in image_data:
                image_url = image_response.url
                image_id = save_image_to_db(
                    current_user.id, prompt, model, size, quality, style
                )
                local_image_url = download_and_store_image(
                    download_dir, image_url, image_id
                )
                image_urls.append(local_image_url)

                # Create and append metadata dictionary for each image
                image_metadata.append(
                    {
                        "id": image_id,
                        "prompt": prompt,
                        "model": model,
                        "size": size,
                        "quality": quality,
                        "style": style,
                        "created_at": datetime.utcnow().strftime(date_format),
                    }
                )

        except Exception as e:
            error_message = str(e)
            db.session.rollback()
            print(f"Error generating image: {error_message}")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if error_message:
            return jsonify({"error_message": error_message, "status": "error"})
        # Return both image URLs and metadata in the response
        return jsonify(
            {
                "image_urls": image_urls,
                "image_metadata": image_metadata,
                "status": "success",
            }
        )

    return render_template(
        "image.html", form=form, image_urls=image_urls, error_message=error_message,
        tooltip=docs_content
    )


@bp.route("/download_image/<uuid:image_id>")
@login_required
def download_image(image_id):
    image_record = GeneratedImage.query.filter_by(
        user_id=current_user.id, id=str(image_id), delete=False
    ).first()

    if not image_record:
        raise NotFound("Image not found or does not belong to the current user")

    download_dir = current_app.config["USER_IMAGE_DIRECTORY"]
    webp_file_name = f"{image_id}.webp"
    webp_file_path = os.path.join(download_dir, webp_file_name)

    if not os.path.exists(webp_file_path):
        raise NotFound("The requested image file does not exist.")

    return send_file(webp_file_path, as_attachment=True)


@bp.route("/history")
@login_required
def image_history():
    user_images = (
        GeneratedImage.query.filter_by(
            user_id=current_user.id, delete=False
        )  # Add delete=False to the filter
        .order_by(GeneratedImage.created_at.desc())
        .limit(15)
        .all()
    )

    image_data = [
        {
            "url": url_for(
                "static", filename=f"temp_img/{img.id}.webp", _external=True
            ),
            "id": img.id,
            "prompt": img.prompt,
            "model": img.model,
            "size": img.size,
            "quality": img.quality,
            "style": img.style,
            "created_at": img.created_at.strftime(date_format),  # Format the datetime
        }
        for img in user_images
    ]

    return jsonify(image_data)


@bp.route("/mark_delete/<uuid:image_id>", methods=["POST"])
@login_required
def mark_delete(image_id):
    image_record = GeneratedImage.query.filter_by(
        user_id=current_user.id, id=str(image_id)
    ).first()

    if not image_record:
        return jsonify({"status": "error", "message": "Image not found"}), 404

    try:
        image_record.delete = True
        db.session.commit()
        return jsonify({"status": "success", "message": "Image marked for deletion"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
