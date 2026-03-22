FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt /tmp/api-req.txt
COPY auto_response/requirements.txt /tmp/ar-req.txt
RUN pip install --no-cache-dir -r /tmp/api-req.txt -r /tmp/ar-req.txt
COPY shared /app/shared
COPY observability /app/observability
COPY auto_response /app/auto_response
COPY api /app/api
ENV PYTHONPATH=/app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
