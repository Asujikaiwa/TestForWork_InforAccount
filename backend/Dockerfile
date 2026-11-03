# Override only if Docker Hub is unreachable, e.g. --build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.13-slim
ARG PYTHON_IMAGE=python:3.13-slim
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so code changes do not invalidate this layer.
COPY pyproject.toml ./
COPY app/__init__.py app/__init__.py
RUN pip install .

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-deps .

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 splitbill
USER splitbill

EXPOSE 8000

# Apply migrations (schema + seed), then serve.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
