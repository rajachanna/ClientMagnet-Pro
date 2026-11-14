FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir . \
    && useradd --uid 10001 --create-home auditor \
    && mkdir -p /data && chown auditor:auditor /data
USER auditor
ENV CM_DB_PATH=/data/clientmagnet.sqlite
EXPOSE 8000
CMD ["uvicorn", "clientmagnet.api:app", "--host", "0.0.0.0", "--port", "8000"]
