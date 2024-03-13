#!/bin/sh

if [ "$FLASK_ENV" = "production" ]; then
  echo "Starting app with Gunicorn in production mode."
  exec gunicorn -k eventlet -w 1 -b 0.0.0.0:8080 wsgi:app
else
  echo "Starting app with Flask development server."
  exec flask run --host=0.0.0.0 --port=8080
fi
