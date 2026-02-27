# Stage 1: builder — install dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project definition and install deps into a prefix
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install --prefix=/install . --no-cache-dir

# Copy application source
COPY app/ ./app/
COPY alembic.ini .

# Stage 2: runtime — minimal image, non-root user
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install curl for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd --no-create-home --shell /bin/false appuser

# Copy installed packages and application from builder
COPY --from=builder /install /usr/local
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic.ini .

# Ensure appuser owns the workdir
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
