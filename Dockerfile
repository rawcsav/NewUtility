FROM python:3.10

WORKDIR /newutil

RUN chown -R www-data:www-data /newutil
COPY . /newutil

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

ENV FLASK_APP=uwsgi.py

# Start uWSGI
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "uwsgi:app", "--bind", "0.0.0.0:8080"]
