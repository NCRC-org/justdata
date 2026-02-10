#!/bin/bash

# Deploy JustData Applications to Cloud Run
# This script deploys BranchSight, BranchMapper, and LendSight

set -e

# Configuration
PROJECT_ID="justdata-ncrc"
REGION="us-east1"
IMAGE_REPO="us-docker.pkg.dev/${PROJECT_ID}/justdata-repo"
IMAGE_TAG="latest"
SERVICE_ACCOUNT="justdata@${PROJECT_ID}.iam.gserviceaccount.com"

# Get service configuration (app_name:port:service_name)
get_service_config() {
    local app_name=$1
    case $app_name in
        branchsight)
            echo "8080:branchsight"
            ;;
        lendsight)
            echo "8082:lendsight"
            ;;
        branchmapper)
            echo "8084:branchmapper"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" >&2
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" >&2
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

# Load environment variables from .env file
load_env_vars() {
    if [ -f .env ]; then
        log "Loading environment variables from .env file..."
        # Export variables from .env file (handles quoted and unquoted values)
        set -a
        source .env
        set +a
        log "Environment variables loaded"
    else
        warn ".env file not found. Some environment variables may be missing."
    fi
}

# Authenticate with Google Cloud
authenticate() {
    log "Setting up Google Cloud authentication..."
    
    gcloud config set project $PROJECT_ID
    log "Project set to: $PROJECT_ID"
    
    # For Docker operations, use user account (needed for Artifact Registry push)
    # Activate user account if available, otherwise use service account
    local user_account=$(gcloud auth list --format="value(account)" | grep -v "@.*\.iam\.gserviceaccount\.com" | head -1)
    if [ -n "$user_account" ]; then
        log "Activating user account for Docker operations: $user_account"
        gcloud config set account "$user_account"
    else
        warn "No user account found. Using service account for Docker operations."
    fi
    
    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker us-docker.pkg.dev --quiet
    gcloud auth configure-docker us-east1-docker.pkg.dev --quiet
    
    # For Cloud Run deployment, we'll switch to justdata service account later
}

# Authenticate with justdata service account for Cloud Run deployment
authenticate_for_deployment() {
    log "Authenticating with justdata service account for Cloud Run deployment..."
    
    local key_file=".secrets/justdata-service-account.json"
    
    if [ ! -f "$key_file" ]; then
        error "Service account key file not found: $key_file"
        exit 1
    fi
    
    # Activate service account for gcloud commands (Cloud Run deployment)
    gcloud auth activate-service-account justdata@${PROJECT_ID}.iam.gserviceaccount.com \
        --key-file="$key_file"
    
    log "Authenticated as: justdata@${PROJECT_ID}.iam.gserviceaccount.com for Cloud Run"
}

# Build and push Docker image using Cloud Build
build_and_push() {
    local app_name=$1
    local service_name=$2
    
    log "Building and pushing Docker image for ${service_name} using Cloud Build..."
    
    # Use Cloud Build to build and push (more reliable than local Docker)
    local image_uri="us-east1-docker.pkg.dev/${PROJECT_ID}/justdata-repo/${service_name}:${IMAGE_TAG}"
    
    # Submit build to Cloud Build
    log "Submitting build to Cloud Build..."
    if ! gcloud builds submit \
        --timeout=20m \
        --substitutions=_APP_NAME=${app_name},_IMAGE_URI=${image_uri} \
        --config=cloudbuild.yaml >&2
    then
        error "Cloud Build failed for ${service_name}"
        exit 1
    fi
    
    log "Image built and pushed successfully: ${image_uri}"
    # Output only the image URI to stdout (no log messages)
    echo "${image_uri}"
}

# Deploy a service to Cloud Run
deploy_service() {
    local app_name=$1
    local port=$2
    local service_name=$3
    local image_uri=$4
    
    # Note: authenticate_for_deployment should be called once before deploying all services
    
    log "Deploying ${service_name} to Cloud Run..."
    
    # Build environment variables string (PORT is set automatically by Cloud Run)
    local env_vars="DEBUG=false,LOG_LEVEL=INFO,PROJECT_ID=${PROJECT_ID},GCP_PROJECT_ID=${PROJECT_ID}"
    
    # Add common environment variables if they exist
    if [ -n "${CLAUDE_API_KEY:-}" ]; then
        env_vars="${env_vars},CLAUDE_API_KEY=${CLAUDE_API_KEY}"
    fi
    
    if [ -n "${SECRET_KEY:-}" ]; then
        env_vars="${env_vars},SECRET_KEY=${SECRET_KEY}"
    fi
    
    # Add BranchMapper-specific environment variables
    if [ "${app_name}" == "branchmapper" ] && [ -n "${CENSUS_API_KEY:-}" ]; then
        env_vars="${env_vars},CENSUS_API_KEY=${CENSUS_API_KEY}"
    fi
    
    # Deploy with service account and environment variables
    gcloud run deploy ${service_name} \
        --image ${image_uri} \
        --platform managed \
        --region ${REGION} \
        --allow-unauthenticated \
        --service-account ${SERVICE_ACCOUNT} \
        --port ${port} \
        --memory 2Gi \
        --cpu 2 \
        --timeout 3600 \
        --max-instances 10 \
        --min-instances 0 \
        --set-env-vars="${env_vars}"
    
    # Get service URL
    local service_url=$(gcloud run services describe ${service_name} \
        --region=${REGION} \
        --format="value(status.url)")
    
    log "${service_name} deployed successfully!"
    log "Service URL: ${service_url}"
    echo ${service_url}
}

# Deploy all services (optimized: build all images first, then deploy)
deploy_all() {
    log "Starting optimized deployment of all services..."
    
    local service_urls=()
    local apps=("branchsight" "lendsight" "branchmapper")
    local image_uris=()
    
    # Step 1: Build all images first (Cloud Build handles parallelization)
    log "Building all Docker images..."
    for app_name in "${apps[@]}"; do
        local config=$(get_service_config $app_name)
        if [ -z "$config" ]; then
            warn "Unknown app: ${app_name}. Skipping..."
            continue
        fi
        
        IFS=':' read -r port service_name <<< "$config"
        
        if [ ! -f "run_${app_name}.py" ]; then
            warn "run_${app_name}.py not found. Skipping ${service_name}..."
            continue
        fi
        
        info "Building image for ${service_name}..."
        local image_uri=$(build_and_push ${app_name} ${service_name})
        image_uris+=("${service_name}:${image_uri}")
        log "✓ Image built: ${image_uri}"
    done
    
    # Step 2: Deploy all services (authenticate once for all deployments)
    authenticate_for_deployment
    
    log "Deploying all services..."
    for entry in "${image_uris[@]}"; do
        IFS=':' read -r service_name image_uri <<< "$entry"
        
        # Find app_name and port for this service
        local app_name=""
        local port=""
        for app in "${apps[@]}"; do
            local config=$(get_service_config $app)
            if [ -n "$config" ]; then
                IFS=':' read -r p s <<< "$config"
                if [ "$s" == "$service_name" ]; then
                    app_name=$app
                    port=$p
                    break
                fi
            fi
        done
        
        if [ -z "$app_name" ] || [ -z "$port" ]; then
            warn "Could not find config for ${service_name}. Skipping..."
            continue
        fi
        
        info "Deploying ${service_name}..."
        local service_url=$(deploy_service ${app_name} ${port} ${service_name} ${image_uri})
        service_urls+=("${service_name}: ${service_url}")
        log "✓ ${service_name} deployed successfully"
    done
    
    # Print summary
    log "=== Deployment Summary ==="
    for url_info in "${service_urls[@]}"; do
        log "${url_info}"
    done
}

# Deploy multiple specific services
deploy_multiple() {
    local services_to_deploy=("$@")
    log "Starting deployment of specified services: ${services_to_deploy[*]}"
    
    local service_urls=()
    
    for app_name in "${services_to_deploy[@]}"; do
        local config=$(get_service_config $app_name)
        if [ -z "$config" ]; then
            warn "Unknown app: ${app_name}. Skipping..."
            continue
        fi
        
        IFS=':' read -r port service_name <<< "$config"
        
        if [ ! -f "run_${app_name}.py" ]; then
            warn "run_${app_name}.py not found. Skipping ${service_name}..."
            continue
        fi
        
        info "Processing ${service_name} (app: ${app_name}, port: ${port})..."
        
        # Build and push
        local image_uri=$(build_and_push ${app_name} ${service_name})
        
        # Deploy
        local service_url=$(deploy_service ${app_name} ${port} ${service_name} ${image_uri})
        service_urls+=("${service_name}: ${service_url}")
        
        log "✓ ${service_name} deployment complete"
        echo ""
    done
    
    # Print summary
    log "=== Deployment Summary ==="
    for url_info in "${service_urls[@]}"; do
        log "${url_info}"
    done
}

# Deploy a single service
deploy_one() {
    local app_name=$1
    
    local config=$(get_service_config $app_name)
    if [ -z "$config" ]; then
        error "Unknown app: ${app_name}"
        error "Available apps: branchsight, lendsight, branchmapper"
        exit 1
    fi
    
    IFS=':' read -r port service_name <<< "$config"
    
    if [ ! -f "run_${app_name}.py" ]; then
        error "run_${app_name}.py not found for ${app_name}"
        exit 1
    fi
    
    info "Deploying single service: ${service_name}"
    local image_uri=$(build_and_push ${app_name} ${service_name})
    deploy_service ${app_name} ${port} ${service_name} ${image_uri}
}

# Main
main() {
    # Load environment variables first
    load_env_vars
    
    check_requirements
    authenticate
    
    # If no arguments or "all", deploy all services
    if [ $# -eq 0 ] || [ "$1" == "all" ]; then
        deploy_all
    # If multiple arguments, deploy those specific services
    elif [ $# -gt 1 ]; then
        deploy_multiple "$@"
    # Single service deployment
    else
        deploy_one $1
    fi
    
    log "Deployment process completed!"
}

# Run main function
main "$@"

