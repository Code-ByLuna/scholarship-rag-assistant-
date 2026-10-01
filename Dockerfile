FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY backend ./backend
COPY scholarship_dataset_ready.json combined_scholarship_schemes_cleaned.json ./
RUN useradd --create-home navigator && mkdir -p /app/var/static && chown -R navigator:navigator /app
USER navigator
EXPOSE 8000
CMD ["sh", "/app/backend/entrypoint.sh"]
