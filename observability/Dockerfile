FROM python:3.12-slim
WORKDIR /app
COPY observability/requirements.txt /app/observability/requirements.txt
RUN pip install --no-cache-dir -r /app/observability/requirements.txt
COPY shared /app/shared
COPY observability /app/observability
ENV PYTHONPATH=/app
EXPOSE 9090
CMD ["sh", "-c", "uvicorn observability.main:app --host 0.0.0.0 --port ${OBSERVABILITY_PORT:-9090}"]
