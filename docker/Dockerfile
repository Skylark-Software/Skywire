# Skywire Server Dockerfile
FROM python:3.11-slim

LABEL maintainer="Jay Brame"
LABEL description="Skywire - Distributed Audio Routing System"

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY skywire/ skywire/
COPY setup.py .

# Install package
RUN pip install -e .

# Expose ports
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Run server
ENTRYPOINT ["python", "-m", "skywire"]
CMD ["--host", "0.0.0.0", "--port", "8765"]
