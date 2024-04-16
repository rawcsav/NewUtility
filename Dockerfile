# Use Python 3.10 as the base image for the initial build stage
FROM python:3.10 AS build

# Set the working directory
WORKDIR /newutil

# Copy requirements.txt first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Use a slim Python 3.10 image as the base for the final stage
FROM python:3.10-slim

# Set the working directory
WORKDIR /newutil

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy the installed Python dependencies from the build stage
COPY --from=build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Copy the application code
COPY . .

# Change ownership of the working directory
RUN chown -R www-data:www-data /newutil

# Set the Flask app environment variable
ENV FLASK_APP=uwsgi.py

# Expose the application port
EXPOSE 8080

# Run the application with Gunicorn and gevent worker
CMD ["gunicorn", "--worker-class", "gevent", "-w", "1", "uwsgi:app", "--bind", "0.0.0.0:8080"]