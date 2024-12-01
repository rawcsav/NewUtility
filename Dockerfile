FROM python:3.10-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=uwsgi.py \
    NLTK_DATA=/usr/local/share/nltk_data

WORKDIR /newutil

# Combine apt operations and use parallel downloads
RUN echo 'Acquire::http::Pipeline-Depth "5";' >> /etc/apt/apt.conf.d/00pipeline && \
    echo 'Acquire::http::Parallel-Queue-Size "5";' >> /etc/apt/apt.conf.d/00parallel

# Cache apt and pip in single layer
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    --mount=type=cache,target=/root/.cache/pip \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    pip install gunicorn eventlet flask && \
    mkdir -p ${NLTK_DATA} && \
    chmod -R 777 ${NLTK_DATA}

# Only copy what's needed
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', download_dir='${NLTK_DATA}'); nltk.download('wordnet', download_dir='${NLTK_DATA}'); nltk.download('averaged_perceptron_tagger', download_dir='${NLTK_DATA}'); nltk.download('omw-1.4', download_dir='${NLTK_DATA}')"

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--preload", "uwsgi:app", "--bind", "0.0.0.0:8080"]