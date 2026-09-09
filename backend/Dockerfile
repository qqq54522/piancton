ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --root-user-action=ignore --index-url "${PIP_INDEX_URL}" -r requirements.txt

COPY backend /app/backend
COPY docs /app/docs
COPY skills /app/skills
COPY taxonomy /app/taxonomy
COPY docker/backend-entrypoint.sh /usr/local/bin/piancton-entrypoint
RUN chmod +x /usr/local/bin/piancton-entrypoint \
    && addgroup --system piancton \
    && adduser --system --ingroup piancton piancton \
    && mkdir -p /data/images \
    && chown -R piancton:piancton /app /data/images

EXPOSE 8000
ENTRYPOINT ["piancton-entrypoint"]
