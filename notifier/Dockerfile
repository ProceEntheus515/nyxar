FROM python:3.12-slim
WORKDIR /app
COPY notifier/requirements.txt /app/notifier/requirements.txt
RUN pip install --no-cache-dir -r /app/notifier/requirements.txt
COPY shared /app/shared
COPY notifier /app/notifier
ENV PYTHONPATH=/app
CMD ["python", "-m", "notifier.main"]
