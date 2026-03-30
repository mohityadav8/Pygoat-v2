# Dockerfile — PyGoat v2 Core Application
# hadolint ignore=DL3008,DL3009

FROM python:3.12-slim

LABEL org.opencontainers.image.title="PyGoat v2"
LABEL org.opencontainers.image.description="OWASP Intentionally Vulnerable Application — Core"
LABEL org.opencontainers.image.source="https://github.com/adeyosemanputra/pygoat"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash pygoat
WORKDIR /app
RUN chown pygoat:pygoat /app

# Install Python dependencies
COPY --chown=pygoat:pygoat requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=pygoat:pygoat . .

# Switch to non-root user
USER pygoat

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Healthcheck — uses the /api/lab/health/ endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/lab/health/')"

CMD ["gunicorn", "pygoat.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
