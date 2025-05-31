# Unified Dockerfile with conditional CUDA support
# Usage:
# For CPU: docker build .
# For GPU: docker build --build-arg USE_CUDA=1 .

ARG USE_CUDA=0
ARG BASE_IMAGE=${USE_CUDA:+"nvidia/cuda:12.0.0-base-ubuntu22.04"}
ARG BASE_IMAGE=${BASE_IMAGE:-"python:3.9-slim"}

# Build stage
FROM ${BASE_IMAGE} AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        python3-pip \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY webroot/server/requirements.txt .

# Build wheels for all requirements
RUN pip3 wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Final stage
FROM ${BASE_IMAGE}

# Create non-root user
RUN useradd -m appuser && \
    mkdir -p /app && \
    chown appuser:appuser /app

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-pip \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and requirements from builder
COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir /wheels/*

# Pass build arg to env var
ARG USE_CUDA
# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    USE_CUDA=$USE_CUDA

# Expose port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Copy entrypoint script and application
COPY docker-entrypoint.sh /app/
COPY . .

# Set proper permissions (do this before switching to non-root user)
RUN chmod +x /app/docker-entrypoint.sh && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

ENTRYPOINT ["/app/docker-entrypoint.sh"]
