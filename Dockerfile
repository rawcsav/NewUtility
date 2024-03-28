FROM python:3.10 as builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.10-slim
RUN useradd -m appuser && \
    chown -R appuser:appuser /home/appuser
USER appuser
WORKDIR /home/appuser/newutil

COPY --from=builder /venv /venv
COPY --chown=appuser:appuser . .

USER root
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*
USER appuser

# Expose the port the app runs on
EXPOSE 8080

# Set environment variables
ENV FLASK_APP=uwsgi.py \
    PATH="/venv/bin:$PATH"

# Start the application using gunicorn with a non-root user
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "uwsgi:app", "--bind", "0.0.0.0:8080"]