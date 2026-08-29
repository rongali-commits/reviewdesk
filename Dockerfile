FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY data ./data
COPY src ./src

RUN pip install --no-cache-dir .

RUN mkdir -p /app/runtime

EXPOSE 8000

CMD ["sh", "-c", "uvicorn reviewdesk.app:app --host 0.0.0.0 --port ${PORT:-8000}"]

