#!/bin/sh

echo "Applying database migrations..."
python manage.py migrate --noinput
python manage.py import_base_exercises

echo "Starting server..."
exec "$@"