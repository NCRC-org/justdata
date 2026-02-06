# Use Python 3.11 slim image
FROM python:3.11-slim

# Build argument to specify which app to run
# If not provided or empty, defaults to unified "justdata" app
ARG APP_NAME=
ENV APP_NAME=${APP_NAME:-justdata}

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Explicitly ensure HUD data directory is present (needed for Population Share calculations)
# The .dockerignore re-includes justdata/data/hud/ but this ensures it's definitely copied
RUN mkdir -p /app/justdata/data/hud && \
    ls -la /app/justdata/data/ 2>/dev/null || true && \
    ls -la /app/justdata/data/hud/ 2>/dev/null || true

# Copy and make startup script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create data directories needed by apps (before changing to non-root user)
RUN mkdir -p /app/justdata/apps/data/reports && \
    mkdir -p /app/justdata/apps/credentials && \
    mkdir -p /app/justdata/data/reports && \
    mkdir -p /app/justdata/data/reports/dataexplorer && \
    mkdir -p /app/justdata/data/reports/lendsight && \
    mkdir -p /app/justdata/data/reports/bizsight && \
    mkdir -p /app/justdata/data/reports/branchsight && \
    mkdir -p /app/justdata/data/reports/mergermeter

# Create non-root user and give ownership of all app files
# Also fix permissions on ALL directories (OneDrive sync can set restrictive perms)
RUN useradd --create-home --shell /bin/bash app && \
    find /app -type d -exec chmod 755 {} \; && \
    find /app -type f -exec chmod 644 {} \; && \
    chmod +x /app/start.sh && \
    chown -R app:app /app
USER app

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Run the startup script which handles PORT variable correctly
CMD ["/app/start.sh"]

