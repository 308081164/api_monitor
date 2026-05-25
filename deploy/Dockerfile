# API Monitor — Phase 2 Docker image
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -e ".[analyze]" \
    && useradd -m -u 1000 sentinel \
    && mkdir -p /data && chown sentinel:sentinel /data

USER sentinel
ENV SENTINEL_DB_PATH=/data/responses.db
ENV SENTINEL_HOST=0.0.0.0
ENV SENTINEL_PORT=8080

EXPOSE 8080
VOLUME ["/data"]

CMD ["api-monitor", "serve", "--host", "0.0.0.0", "--port", "8080"]
