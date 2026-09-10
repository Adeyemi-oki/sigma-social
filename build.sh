#!/usr/bin/env bash
# Render build script for Sigma Social.
#
# Deliberately does NOT run `makemigrations` -- migrations are
# generated during development and committed to the repo; the build
# only ever applies migrations that already exist.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
