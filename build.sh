#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python app.py migrate --run-syncdb
