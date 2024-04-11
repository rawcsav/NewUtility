from app import socketio
from app.tasks.celery_task import celery
from app.models.task_models import Task, ImageTask
from app.modules.image.image_util import generate_images, save_image_to_db, download_compressed_image
from app.modules.auth.auth_util import task_client
from app.modules.user.user_util import get_user_gen_img_directory
from app.utils.logging_util import configure_logging
from app.utils.task_util import make_session


logger = configure_logging()

def process_image(session, image_task, user_id):
    try:
        request_params = {
            "model": image_task.model,
            "prompt": image_task.prompt,
            "n": image_task.n,
            "size": image_task.size,
            "quality": image_task.quality,
            "style": image_task.style,
        }
        client, key_id, error = task_client(session, user_id)
        if error:
            logger.error(f"Client error for user {user_id}: {error}")
            raise Exception(error)

        logger.info(f"Request parameters for image generation: {request_params}")
        user_image_directory = get_user_gen_img_directory(user_id)
        socketio.emit(
            "task_progress",
            {"task_id": image_task.task_id, "message": f"Visualizing {image_task.prompt}..."},
            room=str(user_id),
            namespace="/image",
        )
        image_data = generate_images(
            session=session, user_id=user_id, api_key_id=key_id, client=client, request_params=request_params
        )
        socketio.emit(
            "task_progress",
            {"task_id": image_task.task_id, "message": f"Adding the final touches..."},
            room=str(user_id),
            namespace="/image",
        )
        if not image_data:
            logger.error(f"No image data received for task_id={image_task.task_id}")
            return

        for image_response in image_data:
            image_url = image_response.url
            if not image_url:
                logger.error(f"No image URL received for task_id={image_task.task_id}")
                continue

            image_id = save_image_to_db(
                session,
                user_id,
                image_task.prompt,
                image_task.model,
                image_task.size,
                image_task.quality,
                image_task.style,
                image_task.task_id,
            )
            if not image_id:
                logger.error(f"Failed to save image metadata to DB for task_id={image_task.task_id}")
                continue

            file_name = download_compressed_image(user_image_directory, image_url, image_id)

            if file_name:
                socketio.emit(
                    "task_complete",
                    {
                        "task_id": image_task.task_id,
                        "message": f"Admiring my masterpiece...",
                        "status": "completed",
                        "image": {"user_id": user_id, "file_name": file_name},
                    },
                    room=str(user_id),
                    namespace="/image",
                )
                return file_name
            else:
                logger.error(
                    f"Failed to download and store image for task_id={image_task.task_id} and image_id={image_id}"
                )
                continue

        logger.info(f"Image processing completed for task_id={image_task.task_id}")

    except Exception as e:
        logger.error(f"Error processing image for task_id={image_task.task_id}: {e}")
        socketio.emit(
            "task_update",
            {"task_id": image_task.task_id, "status": "error", "error": str(e)},
            room=str(user_id),
            namespace="/image",
        )
        raise e


@celery.task(time_limit=60)
def process_image_task(task_id):
    session = make_session()
    try:
        task = session.query(Task).filter_by(id=task_id).one()
        image_task = session.query(ImageTask).filter_by(task_id=task_id).first()
        if task and image_task:
            try:
                logger.info(f"Processing image task {task_id} for user {task.user_id}")
                socketio.emit(
                    "task_progress",
                    {"task_id": image_task.task_id, "message": f"Preparing the studio..."},
                    room=str(task.user_id),
                    namespace="/image",
                )
                success = process_image(session, image_task, task.user_id)
                if success:
                    logger.info(f"Task {task_id} status updated to completed")
                    return True
                else:
                    logger.error(f"Task {task_id} failed during processing")
                    return False
            except Exception as e:
                session.rollback()
                logger.error(f"Error processing image task {task_id}: {e}")
                socketio.emit(
                    "task_update",
                    {"task_id": image_task.task_id, "status": "error", "error": str(e)},
                    room=str(task.user_id),
                    namespace="/image",
                )
                return False
        else:
            logger.error(f"Task {task_id} is not pending or image task not found")
            return False
    finally:
        session.remove()  # Dispose of the session correctly

