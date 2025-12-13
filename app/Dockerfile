FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg2-binary are already bundled; keep image small.
RUN pip install --no-cache-dir --upgrade pip

# Install runtime deps (kept inline so you can stay with 1 main.py + 1 index.html)
RUN pip install --no-cache-dir \
    flask==3.0.3 \
    gunicorn==22.0.0 \
    boto3==1.34.162 \
    psycopg2-binary==2.9.9

COPY main.py /app/main.py
COPY index.html /app/index.html

EXPOSE 8000

# Gunicorn for production-ish container runtime
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60", "main:app"]
