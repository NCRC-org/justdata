#!/bin/bash

# JustData Deployment Script
# This script deploys the JustData application to Google Cloud Run

set -e

# Configuration
PROJECT_ID="hdma1-242116"
REGION="us-east1"
SERVICE_NAME="justdata"
IMAGE_REPO="us-docker.pkg.dev/${PROJECT_ID}/justdata-repo/${SERVICE_NAME}"
IMAGE_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check if required tools are installed
check_requirements() {
    log "Checking requirements..."
    
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    log "Requirements check passed"
}

# Authenticate with Google Cloud
authenticate() {
    log "Authenticating with Google Cloud..."
    
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log "Already authenticated with Google Cloud"
    else
        log "Please authenticate with Google Cloud..."
        gcloud auth login
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    log "Project set to: $PROJECT_ID"
}

# Build and push Docker image
build_and_push() {
    log "Building Docker image..."
    
    # Build the image
    docker build -t $SERVICE_NAME:$IMAGE_TAG .
    
    # Tag for Google Container Registry
    docker tag $SERVICE_NAME:$IMAGE_TAG $IMAGE_REPO:$IMAGE_TAG
    
    log "Pushing image to Google Container Registry..."
    docker push $IMAGE_REPO:$IMAGE_TAG
    
    log "Image pushed successfully: $IMAGE_REPO:$IMAGE_TAG"
}

# Deploy to Cloud Run
deploy() {
    log "Deploying to Cloud Run..."
    
    gcloud run deploy $SERVICE_NAME \
        --image $IMAGE_REPO:$IMAGE_TAG \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --port 8000 \
        --memory 2Gi \
        --cpu 2 \
        --timeout 3600 \
        --max-instances 10 \
        --set-env-vars="DEBUG=false,LOG_LEVEL=INFO" \
        --update-env-vars="PROJECT_ID=$PROJECT_ID"
    
    log "Deployment completed successfully!"
}

# Get service URL
get_service_url() {
    log "Getting service URL..."
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    log "Service URL: $SERVICE_URL"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Wait a bit for service to be ready
    sleep 30
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    
    if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
        log "Health check passed! Service is running."
    else
        warn "Health check failed. Service might still be starting up."
    fi
}

# Main deployment flow
main() {
    log "Starting JustData deployment..."
    
    check_requirements
    authenticate
    build_and_push
    deploy
    get_service_url
    health_check
    
    log "Deployment completed successfully!"
    log "You can access your service at: $SERVICE_URL"
}

# Run main function
main "$@"
