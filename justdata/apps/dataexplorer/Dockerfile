# DataExplorer 2.0 Dockerfile
# Production-ready container for DataExplorer wizard interface
# Supports deployment to Docker-based hosting services (after Render testing)

FROM python:3.11-slim

# Set metadata
LABEL maintainer="NCRC JustData Team"
LABEL description="DataExplorer 2.0 - Interactive Financial Data Dashboard"
LABEL version="2.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
# Required for some Python packages (pandas, numpy, etc.)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Copy shared directory first (for better Docker layer caching)
# This includes shared utilities, templates, and static files
COPY shared/ /app/shared/

# Copy DataExplorer app files
COPY apps/dataexplorer/ /app/apps/dataexplorer/

# Note: Root-level files are not needed for DataExplorer
# If needed in the future, copy them individually or use a specific directory

# Install Python dependencies
# Install app-specific requirements
RUN pip install --no-cache-dir -r apps/dataexplorer/requirements.txt

# Create non-root user for security
RUN useradd -m -u 1000 dataexplorer && \
    chown -R dataexplorer:dataexplorer /app

# Switch to non-root user
USER dataexplorer

# Expose port (DataExplorer default port)
EXPOSE 8085

# Health check
# Uses Python's urllib (built-in) instead of requests for reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8085/health', timeout=5)" || exit 1

# Default command - use gunicorn for production
# This can be overridden in docker-compose.yml or when running the container
# Use 'application' export from app.py for gunicorn compatibility
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8085", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--preload", \
     "apps.dataexplorer.app:application"]
