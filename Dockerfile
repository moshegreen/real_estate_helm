FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md* ./
COPY src ./src
COPY web ./web
COPY schema ./schema

RUN pip install --no-cache-dir .

EXPOSE 8765

CMD ["real-estate-helm-server", "--host", "0.0.0.0", "--port", "8765", "--data-dir", "/data"]
