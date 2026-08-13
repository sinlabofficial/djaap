#!/bin/bash
set -e

cd backend

# Calculate workers based on CPU cores
WORKERS=${GUNICORN_WORKERS:-4}

echo "Starting Gunicorn with $WORKERS workers..."
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers $WORKERS \
    --timeout 60 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    config.wsgi:application
