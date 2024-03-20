# Use an official Python runtime as a base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /newutil

RUN chown -R www-data:www-data /newutil
COPY . /newutil

# Install FFmpeg (if needed for your app) and any needed packages specified in requirements.txt
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Expose the port uWSGI will listen on
EXPOSE 8080

# Define environment variable
ENV FLASK_APP=uwsgi.py

# Start uWSGI
CMD ["python", "uwsgi.py"]
