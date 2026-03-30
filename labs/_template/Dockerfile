# labs/_template/Dockerfile
# Scaffold for lab microservice containers
# Copy to labs/<lab_id>/Dockerfile and modify APP_MODULE

FROM python:3.12-slim

LABEL org.opencontainers.image.description="PyGoat v2 — Lab Microservice"

# Install deps
RUN pip install --no-cache-dir flask flask-sqlalchemy pyjwt pyyaml argon2-cffi requests

WORKDIR /lab

# Non-root user for lab container
RUN useradd --create-home --shell /bin/sh labuser
RUN chown labuser:labuser /lab
USER labuser

COPY --chown=labuser:labuser . .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT/health')"

# Override APP_MODULE in docker-compose.yml per-lab
ENV APP_MODULE=app:app
ENV PORT=8001

CMD ["sh", "-c", "python -m flask --app ${APP_MODULE} run --host=0.0.0.0 --port=${PORT}"]
