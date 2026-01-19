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

# Copy and make startup script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create data directories needed by apps (before changing to non-root user)
RUN mkdir -p /app/justdata/apps/data/reports && \
    mkdir -p /app/justdata/apps/credentials && \
    mkdir -p /app/justdata/data/reports

# Create non-root user and give ownership of all app files
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Run the startup script which handles PORT variable correctly
CMD ["/app/start.sh"]

