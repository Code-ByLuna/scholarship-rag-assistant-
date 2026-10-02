FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
    VECTOR_INDEX_DIR=/app/var/index \
    DJANGO_DEBUG=false DB_ENGINE=mysql TRUST_PROXY_HEADERS=true DJANGO_SERVE_STATIC=true
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config default-libmysqlclient-dev ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
RUN useradd --create-home --uid 1000 navigator \
    && mkdir -p /app/var/static /opt/huggingface \
    && chown -R navigator:navigator /app /opt/huggingface
COPY --chown=navigator:navigator backend ./backend
COPY --chown=navigator:navigator data/scholarship_dataset_ready.json data/combined_scholarship_schemes_cleaned.json ./data/
COPY --chown=navigator:navigator deploy/rag-assets.json ./deploy/rag-assets.json
COPY --chown=navigator:navigator scripts/provision_rag_assets.py ./scripts/provision_rag_assets.py
COPY --chown=navigator:navigator var/index/CURRENT ./var/index/CURRENT
COPY --chown=navigator:navigator var/index/faac7d4df3034bafae61db8e52553481/vectors.faiss var/index/faac7d4df3034bafae61db8e52553481/chunks.json var/index/faac7d4df3034bafae61db8e52553481/metadata.json ./var/index/faac7d4df3034bafae61db8e52553481/
USER navigator
# Only the build downloads weights. Normal execution is offline for model assets.
RUN HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python scripts/provision_rag_assets.py --download-model
RUN python scripts/provision_rag_assets.py --check-model
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl --fail --silent -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/api/health/live || exit 1
CMD ["sh", "/app/backend/entrypoint.sh"]
