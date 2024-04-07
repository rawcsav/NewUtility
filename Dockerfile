FROM python:3.10

WORKDIR /newutil
COPY requirements.txt /rawcon/

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

COPY . /newutil
RUN groupadd -r newutil && newutil --no-log-init -r -g newutil newutil \
    && chown -R newutil:newutil /rawcon \


ENV FLASK_APP=uwsgi.py

# Start uWSGI
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "uwsgi:app", "--bind", "0.0.0.0:8080"]
