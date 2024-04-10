import os
from flask import jsonify, Blueprint, render_template, send_file, url_for, current_app, request, send_from_directory
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound
from markdown2 import markdown
from app import db
from app.models.image_models import GeneratedImage
from app.models.task_models import ImageTask, Task
from app.modules.user.user_util import get_user_gen_img_directory
from app.utils.forms_util import GenerateImageForm
from app.tasks.image_task import process_image_task

image_bp = Blueprint("image_bp", __name__, template_folder="templates", static_folder="static", url_prefix="/image")

date_format = "%b %d, %Y at %I:%M %p"


@image_bp.route("/", methods=["GET", "POST"])
@login_required
def generate_image():
    form = GenerateImageForm()
    error_message = None
    markdown_file_path = os.path.join(current_app.root_path, image_bp.static_folder, "image.md")

    with open(markdown_file_path, "r") as file:
        markdown_content = file.read()
    docs_content = markdown(markdown_content)
    if form.validate_on_submit():
        try:
            # Gather request details
            prompt = form.prompt.data
            model = form.model.data or "dall-e-3"
            n = form.n.data or 1
            size = form.size.data or "1024x1024"
            quality = form.quality.data if model.startswith("dall-e-3") else None
            style = form.style.data if model.startswith("dall-e-3") else None

            # Create a new Task for image generation
            new_task = Task(type="Image", status="pending", user_id=current_user.id)
            db.session.add(new_task)
            db.session.flush()

            # Create a new ImageTask
            new_image_task = ImageTask(
                task_id=new_task.id, prompt=prompt, model=model, size=size, quality=quality, style=style, n=n
            )
            db.session.add(new_image_task)
            db.session.commit()
            process_image_task.apply_async(kwargs={"task_id": new_task.id}, countdown=5)  # Add a delay of 5 seconds
        except Exception as e:
            error_message = str(e)
            db.session.rollback()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if error_message:
            return jsonify({"error_message": error_message, "status": "error"})
        return jsonify({"message": "Image Processing...", "status": "success"})

    return render_template("image.html", form=form, error_message=error_message, tooltip=docs_content)


@image_bp.route("/download_image/<uuid:image_id>")
@login_required
def download_image(image_id):
    image_record = GeneratedImage.query.filter_by(user_id=current_user.id, id=str(image_id)).first()

    if not image_record:
        raise NotFound("Image not found or does not belong to the current user")

    download_dir = get_user_gen_img_directory(current_user.id)
    webp_file_name = f"{image_id}.webp"
    webp_file_path = os.path.join(download_dir, webp_file_name)

    if not os.path.exists(webp_file_path):
        raise NotFound("The requested image file does not exist.")

    return send_file(webp_file_path, as_attachment=True)


@image_bp.route("/history")
@login_required
def image_history():
    user_images = (
        GeneratedImage.query.filter_by(user_id=current_user.id, delete=False)  # Add delete=False to the filter
        .order_by(GeneratedImage.created_at.desc())
        .limit(15)
        .all()
    )
    image_data = [
        {
            "url": url_for(
                "image_bp.serve_generated_image", filename=f"{img.id}.webp", user_id=current_user.id, _external=True
            ),
            "id": img.id,
            "prompt": img.prompt,
            "model": img.model,
            "size": img.size,
            "quality": img.quality,
            "style": img.style,
            "created": img.created_at.strftime(date_format),  # Format the datetime
        }
        for img in user_images
    ]

    return jsonify(image_data)


@image_bp.route("/user_images/<user_id>/<path:filename>")
def serve_generated_image(user_id, filename):
    user_image_directory = get_user_gen_img_directory(user_id)
    return send_from_directory(user_image_directory, filename)


@image_bp.route("/user_urls/<user_id>/<path:filename>")
def serve_generated_url(user_id, filename):
    return url_for("image_bp.serve_generated_image", filename=filename, user_id=user_id, _external=True)


@image_bp.route("/mark_delete/<uuid:image_id>", methods=["POST"])
@login_required
def mark_delete(image_id):
    image_record = GeneratedImage.query.filter_by(user_id=current_user.id, id=str(image_id), delete=False).first()

    if not image_record:
        return jsonify({"status": "error", "message": "Image not found"}), 404

    try:
        image_record.delete = True
        db.session.commit()
        return jsonify({"status": "success", "message": "Image marked for deletion"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
