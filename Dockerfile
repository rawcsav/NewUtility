# Use an intermediate build stage to install dependencies
FROM python:3.10 as builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

# Start from a slim version of the Python image for the final image
FROM python:3.10-slim

# Create a non-root user but set the working directory to match the original setup
RUN useradd -m appuser

# Switch to root to perform privileged operations
USER root

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /venv /venv

# Set the working directory to /newutil to match the original setup
WORKDIR /newutil

# Copy your application code and adjust ownership
COPY --chown=appuser:appuser . .

# Ensure the non-root user has access to the necessary directories
RUN chown -R appuser:appuser /newutil

# Switch back to the non-root user for running the application
USER appuser

# Expose the application port
EXPOSE 8080

# Set environment variables
ENV FLASK_APP=uwsgi.py \
    PATH="/venv/bin:$PATH"

# Start the application using gunicorn with a non-root user
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "uwsgi:app", "--bind", "0.0.0.0:8080"]