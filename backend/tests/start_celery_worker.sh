#!/bin/bash
# Start Celery worker for InsurAI Demo MVP

echo "Starting Celery worker..."
echo "Make sure Redis is running on localhost:6379"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Celery worker with auto-reload for development
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=main-queue,ai-queue \
    --pool=solo

# Note: --pool=solo is used for development on systems without proper multiprocessing support
# For production, use --pool=prefork or --pool=gevent
