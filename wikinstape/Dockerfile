FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirments.txt .
RUN pip install --no-cache-dir -r requirments.txt

COPY . .

CMD ["gunicorn", "wikinstape.wsgi:application", "--bind", "0.0.0.0:8000"]
