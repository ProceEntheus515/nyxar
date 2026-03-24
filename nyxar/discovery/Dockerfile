FROM python:3.12-slim
WORKDIR /app
COPY nyxar /app/nyxar
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "nyxar.discovery.engine", "--full-discovery"]
