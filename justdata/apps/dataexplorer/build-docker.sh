#!/bin/bash
# DataExplorer Docker Build Script
# Builds and optionally pushes the Docker image

set -e

# Configuration
IMAGE_NAME="dataexplorer"
VERSION="${1:-2.0.0}"
REGISTRY="${2:-}"  # Optional: e.g., "gcr.io/project-id" or "account.dkr.ecr.region.amazonaws.com"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Building DataExplorer Docker Image${NC}"
echo -e "Version: ${GREEN}${VERSION}${NC}"
echo ""

# Navigate to repository root (assuming script is in apps/dataexplorer/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "${SCRIPT_DIR}/../.." && pwd )"

cd "${REPO_ROOT}"

# Build the image
echo -e "${BLUE}Building Docker image...${NC}"
docker build \
    -f apps/dataexplorer/Dockerfile \
    -t "${IMAGE_NAME}:${VERSION}" \
    -t "${IMAGE_NAME}:latest" \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful!${NC}"
    echo ""
    echo -e "Image: ${GREEN}${IMAGE_NAME}:${VERSION}${NC}"
    echo -e "Image: ${GREEN}${IMAGE_NAME}:latest${NC}"
else
    echo -e "${YELLOW}✗ Build failed${NC}"
    exit 1
fi

# Optionally push to registry
if [ -n "${REGISTRY}" ]; then
    echo ""
    echo -e "${BLUE}Pushing to registry: ${REGISTRY}${NC}"
    
    # Tag for registry
    docker tag "${IMAGE_NAME}:${VERSION}" "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
    docker tag "${IMAGE_NAME}:latest" "${REGISTRY}/${IMAGE_NAME}:latest"
    
    # Push
    docker push "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
    docker push "${REGISTRY}/${IMAGE_NAME}:latest"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Push successful!${NC}"
        echo ""
        echo -e "Registry image: ${GREEN}${REGISTRY}/${IMAGE_NAME}:${VERSION}${NC}"
    else
        echo -e "${YELLOW}✗ Push failed${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "To run the container:"
echo "  docker run -d --name dataexplorer -p 8085:8085 ${IMAGE_NAME}:${VERSION}"
