# LenderProfile Dockerfile
# Production-ready container for Lender Intelligence Reports
# Supports deployment to Docker-based hosting services

FROM python:3.11-slim

# Set metadata
LABEL maintainer="NCRC JustData Team"
LABEL description="LenderProfile - Comprehensive Lender Intelligence Reports"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
# Required for some Python packages
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

# Copy LenderProfile app files
COPY apps/lenderprofile/ /app/apps/lenderprofile/

# Install Python dependencies
# Install app-specific requirements
RUN pip install --no-cache-dir -r apps/lenderprofile/requirements.txt

# Create non-root user for security
RUN useradd -m -u 1000 lenderprofile && \
    chown -R lenderprofile:lenderprofile /app

# Switch to non-root user
USER lenderprofile

# Expose port (LenderProfile default port)
EXPOSE 8086

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8086/health', timeout=5)" || exit 1

# Default command - use gunicorn for production
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8086", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "300", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "apps.lenderprofile.run:application"]
