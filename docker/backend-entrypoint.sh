#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  mkdir -p /data/images/.staging /data/images/.trash /data/images/.thumbnails
  chown -R piancton:piancton /data/images
  exec su -s /bin/sh piancton -c 'alembic upgrade head && python -m scripts.seed_taxonomy && exec uvicorn app.main:app --host 0.0.0.0 --port 8000'
fi

alembic upgrade head
python -m scripts.seed_taxonomy
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
