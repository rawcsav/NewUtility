FROM python:3.10

WORKDIR /newutil
COPY requirements.txt /newutil/

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Create a group and user 'newutil'
RUN groupadd -r newutil && \
    useradd --no-log-init -r -g newutil newutil && \
    chown -R newutil:newutil /newutil

# Switch to the non-root user
USER newutil

# Set environment variables
ENV FLASK_APP=uwsgi.py

# Start uWSGI
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "uwsgi:app", "--bind", "0.0.0.0:8080"]
