#!/bin/bash

# JustData Unified Cloud Run Deployment Script
# This script deploys the unified JustData application to Google Cloud Run

set -e

# Ensure we're using bash 4+ for associative arrays, or use alternative approach
if [ "${BASH_VERSION%%.*}" -lt 4 ]; then
    # Fallback: use a simple approach without associative arrays
    USE_ASSOC_ARRAYS=false
else
    USE_ASSOC_ARRAYS=true
fi

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-hdma1-242116}"
REGION="${GCP_REGION:-us-east1}"
SERVICE_NAME="${SERVICE_NAME:-justdata-test}"
IMAGE_REPO="us-east1-docker.pkg.dev/${PROJECT_ID}/justdata-repo/${SERVICE_NAME}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-justdata@${PROJECT_ID}.iam.gserviceaccount.com}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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
    
    log "Requirements check passed"
}

# Authenticate with Google Cloud
authenticate() {
    log "Setting up Google Cloud authentication..."
    
    gcloud config set project $PROJECT_ID
    log "Project set to: $PROJECT_ID"
    
    # Configure Docker to use gcloud as a credential helper for Artifact Registry
    gcloud auth configure-docker us-east1-docker.pkg.dev --quiet
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        warn "No active authentication found. Attempting to authenticate..."
        gcloud auth login --no-launch-browser
    fi
    
    log "Authentication setup complete"
}

# Build and push Docker image using Cloud Build
build_and_push() {
    log "Building and pushing Docker image using Cloud Build..."
    
    local image_uri="${IMAGE_REPO}:${IMAGE_TAG}"
    
    # Submit build to Cloud Build (unified app, no APP_NAME needed)
    log "Submitting build to Cloud Build..."
    if ! gcloud builds submit \
        --timeout=20m \
        --substitutions=_APP_NAME=,_IMAGE_URI=${image_uri} \
        --config=cloudbuild.yaml >&2
    then
        error "Cloud Build failed"
        exit 1
    fi
    
    log "Image built and pushed successfully: ${image_uri}"
    echo "${image_uri}"
}

# Load environment variables from .env file
# Returns path to JSON file for use with --env-vars-file
load_env_vars() {
    local env_file=$(mktemp)
    
    # Track which keys we've added to avoid duplicates
    local added_keys_file=$(mktemp)
    
    # Start JSON file - use JSON format which Cloud Run accepts
    echo "{" > "$env_file"
    local first=true
    
    # Add required Cloud Run variables first (these take precedence)
    echo "\"PROJECT_ID\": \"${PROJECT_ID}\"" >> "$env_file"
    echo "PROJECT_ID" >> "$added_keys_file"
    first=false
    echo ",\"GCP_PROJECT_ID\": \"${PROJECT_ID}\"" >> "$env_file"
    echo "GCP_PROJECT_ID" >> "$added_keys_file"
    echo ",\"DEBUG\": \"false\"" >> "$env_file"
    echo "DEBUG" >> "$added_keys_file"
    echo ",\"LOG_LEVEL\": \"INFO\"" >> "$env_file"
    echo "LOG_LEVEL" >> "$added_keys_file"
    
    if [ -f .env ]; then
        log "Loading environment variables from .env file..."
        # Read .env file line by line
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "$line" ]] && continue
            
            # Remove leading/trailing whitespace
            line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [[ -z "$line" ]] && continue
            
            # Split on first = sign only (values may contain =)
            if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
                key="${BASH_REMATCH[1]}"
                value="${BASH_REMATCH[2]}"
            else
                # No = sign found, skip this line
                continue
            fi
            
            # Remove leading/trailing whitespace from key
            key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            [[ -z "$key" ]] && continue
            
            # Skip if we've already added this key (required vars take precedence)
            if grep -q "^${key}$" "$added_keys_file" 2>/dev/null; then
                continue
            fi

            # Skip variables that are configured as Secret Manager references in Cloud Run
            # These cannot be overwritten with string literals
            if [ "$key" = "GOOGLE_APPLICATION_CREDENTIALS_JSON" ] || \
               [ "$key" = "CLAUDE_API_KEY" ] || \
               [ "$key" = "ANTHROPIC_API_KEY" ] || \
               [ "$key" = "OPENAI_API_KEY" ] || \
               [ "$key" = "CENSUS_API_KEY" ]; then
                continue
            fi
            
            # Handle value - preserve everything after first = sign
            if [ -n "$value" ]; then
                # Remove leading/trailing whitespace from value
                value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                # Remove quotes from value if present (but preserve content)
                value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                # Remove any trailing whitespace again after quote removal
                value=$(echo "$value" | sed 's/[[:space:]]*$//')
            fi
            
            # Skip if value is empty after processing
            [[ -z "$value" ]] && continue
            
            # Handle newlines (replace with space, then collapse multiple spaces)
            value=$(printf '%s' "$value" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/[[:space:]]*$//')
            
            # Escape special JSON characters: backslashes, quotes, newlines
            # Escape backslashes first, then quotes, then newlines
            value=$(echo "$value" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed 's/\n/\\n/g' | sed 's/\r/\\r/g' | sed 's/\t/\\t/g')
            
            # Add to JSON file with proper comma handling
            if [ "$first" = true ]; then
                echo "\"${key}\": \"${value}\"" >> "$env_file"
                first=false
            else
                echo ",\"${key}\": \"${value}\"" >> "$env_file"
            fi
            
            echo "$key" >> "$added_keys_file"
        done < .env
        
        # Debug: Verify critical API keys were loaded
        log "Verifying critical environment variables..."
        if grep -q "CENSUS_API_KEY" "$env_file" 2>/dev/null; then
            log "✓ CENSUS_API_KEY found in deployment config"
        else
            warn "✗ CENSUS_API_KEY NOT found - Census data will not be available"
        fi
        if grep -q "CLAUDE_API_KEY\|ANTHROPIC_API_KEY" "$env_file" 2>/dev/null; then
            log "✓ CLAUDE_API_KEY/ANTHROPIC_API_KEY found in deployment config"
        else
            warn "✗ CLAUDE_API_KEY/ANTHROPIC_API_KEY NOT found - AI insights will not be available"
        fi
        
        log "Environment variables loaded from .env"
    else
        warn ".env file not found. Using minimal environment variables."
    fi
    
    # Close JSON object
    echo "}" >> "$env_file"
    
    # Clean up temp file
    rm -f "$added_keys_file"
    
    echo "$env_file"
}

# Deploy to Cloud Run
deploy() {
    local image_uri=$1
    local env_file=$2
    
    log "Deploying ${SERVICE_NAME} to Cloud Run..."
    
    # Build gcloud run deploy command arguments
    local deploy_args=(
        "deploy" "${SERVICE_NAME}"
        "--image" "${image_uri}"
        "--platform" "managed"
        "--region" "${REGION}"
        "--allow-unauthenticated"
        "--service-account" "${SERVICE_ACCOUNT}"
        "--port" "8080"
        "--memory" "2Gi"
        "--cpu" "2"
        "--timeout" "3600"
        "--max-instances" "10"
        "--min-instances" "0"
    )
    
    # Add environment variables file if provided
    if [ -n "$env_file" ] && [ -f "$env_file" ]; then
        deploy_args+=("--env-vars-file" "${env_file}")
    fi
    
    # Execute deployment
    gcloud run "${deploy_args[@]}"
    
    # Clean up temp file
    if [ -n "$env_file" ] && [ -f "$env_file" ]; then
        rm -f "$env_file"
    fi
    
    log "Deployment completed successfully!"
}

# Get service URL
get_service_url() {
    log "Getting service URL..."
    local service_url=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --format="value(status.url)" 2>/dev/null)
    
    if [ -n "$service_url" ]; then
        log "Service URL: ${service_url}"
        echo "$service_url"
    else
        warn "Could not retrieve service URL"
        echo ""
    fi
}

# Verify environment variables are set in Cloud Run
verify_env_vars() {
    log "Checking environment variables in Cloud Run service..."
    
    # Get environment variables in a simple format
    local env_output=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --format="get(spec.template.spec.containers[0].env)" 2>/dev/null)
    
    if [ -z "$env_output" ]; then
        warn "Could not retrieve environment variables from Cloud Run service"
        return
    fi
    
    # Check for critical API keys
    if echo "$env_output" | grep -q "CENSUS_API_KEY"; then
        log "✓ CENSUS_API_KEY is set in Cloud Run"
    else
        warn "✗ CENSUS_API_KEY is NOT set in Cloud Run"
    fi
    
    if echo "$env_output" | grep -q "CLAUDE_API_KEY\|ANTHROPIC_API_KEY"; then
        log "✓ CLAUDE_API_KEY/ANTHROPIC_API_KEY is set in Cloud Run"
    else
        warn "✗ CLAUDE_API_KEY/ANTHROPIC_API_KEY is NOT set in Cloud Run"
    fi
}

# Health check
health_check() {
    local service_url=$1
    
    if [ -z "$service_url" ]; then
        warn "No service URL provided, skipping health check"
        return
    fi
    
    log "Performing health check (with timeout protection)..."
    
    # Wait a bit for service to be ready
    sleep 5
    
    local max_attempts=2
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Use timeout command with explicit timeout to prevent hanging
        # Check if timeout command exists, if not use curl's built-in timeout
        if command -v timeout >/dev/null 2>&1; then
            if timeout 5 curl -f -s --max-time 5 "${service_url}/health" > /dev/null 2>&1; then
                log "Health check passed! Service is running."
                return 0
            fi
        else
            # Fallback: use curl's --max-time option
            if curl -f -s --max-time 5 "${service_url}/health" > /dev/null 2>&1; then
                log "Health check passed! Service is running."
                return 0
            fi
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            warn "Health check attempt ${attempt}/${max_attempts} failed. Retrying..."
            sleep 3
        fi
        attempt=$((attempt + 1))
    done
    
    warn "Health check failed after ${max_attempts} attempts. Service might still be starting up."
    warn "You can manually check the service at: ${service_url}/health"
    return 1
}

# Main deployment flow
main() {
    log "Starting JustData unified deployment to Cloud Run..."
    log "Service: ${SERVICE_NAME}"
    log "Project: ${PROJECT_ID}"
    log "Region: ${REGION}"
    echo ""
    
    check_requirements
    authenticate
    
    # Build and push image
    local image_uri=$(build_and_push)
    
    # Load environment variables (returns path to YAML file)
    local env_file=$(load_env_vars)
    
    # Deploy to Cloud Run
    deploy "$image_uri" "$env_file"
    
    # Verify environment variables were set
    log "Verifying environment variables in deployed service..."
    verify_env_vars
    
    # Get service URL
    local service_url=$(get_service_url)
    
    # Perform health check
    health_check "$service_url"
    
    echo ""
    log "=== Deployment Summary ==="
    log "Service: ${SERVICE_NAME}"
    log "Region: ${REGION}"
    log "Image: ${image_uri}"
    if [ -n "$service_url" ]; then
        log "URL: ${service_url}"
        log ""
        log "You can access your service at: ${service_url}"
        log "Health check: ${service_url}/health"
    fi
    log "=========================="
}

# Run main function
main "$@"

