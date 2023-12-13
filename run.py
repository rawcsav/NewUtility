import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(
        port=8080,
        host='localhost',
        static_files={
            '/static': '/Users/gavinmason/PycharmProjects/SwissAI/app/static'},
        ssl_context=('cert.pem', 'key.pem')
    )
