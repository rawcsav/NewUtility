from app import db
from app.database import User, GeneratedImage
from datetime import datetime, timedelta
import os

with app.app_context():
    current_time = datetime.utcnow()
    stale_threshold = current_time - timedelta(hours=24)

    try:
        stale_users = User.query.filter(
            User.email_confirmed == False,
            User.created_at < stale_threshold
        ).all()

        old_images = GeneratedImage.query.filter(
            GeneratedImage.created_at < stale_threshold
        ).all()

        for user in stale_users:
            db.session.delete(user)

        for image in old_images:
            try:
                if image.uuid:
                    download_dir = app.config['USER_IMAGE_DIRECTORY']
                    temp_file_path = os.path.join(download_dir,
                                                  f"{str(image.uuid)}.webp")
                    os.remove(temp_file_path)
            except Exception as e:
                print(f"Error deleting image file: {e}")

            # Delete the image entry from the database
            db.session.delete(image)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting old images: {e}")
