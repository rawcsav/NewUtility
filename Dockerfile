# Use an official Python runtime as the base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app
# Install FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg
# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8080

# Define environment variable
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production

# Copy startup script
COPY start.sh /start.sh

# Make the script executable
RUN chmod +x /start.sh

# Use the startup script to boot the app
CMD ["/start.sh"]
