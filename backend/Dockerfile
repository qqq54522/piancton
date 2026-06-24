ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY skills /app/skills
COPY taxonomy /app/taxonomy
COPY docker/backend-entrypoint.sh /usr/local/bin/piancton-entrypoint
RUN chmod +x /usr/local/bin/piancton-entrypoint \
    && addgroup --system piancton \
    && adduser --system --ingroup piancton piancton \
    && mkdir -p /data/images \
    && chown -R piancton:piancton /app /data/images

USER piancton

EXPOSE 8000
ENTRYPOINT ["piancton-entrypoint"]
