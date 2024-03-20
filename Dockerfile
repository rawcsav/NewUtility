FROM python:3.11

WORKDIR /newutil

RUN chown -R www-data:www-data /newutil
COPY . /newutil

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# Define environment variable
ENV FLASK_APP=uwsgi.py

# Start uWSGI
CMD ["python", "uwsgi.py"]
