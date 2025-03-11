#!/bin/bash
set -e

# Configuration
IMAGE_NAME=${1:-"goranlr/robotea"}
TAG=${2:-"latest"}
PUSH=${3:-"yes"}
PRESERVE_DATA=${4:-"yes"}  # Default to preserving data

echo "Building Gitea with Parquet support..."
echo "Image: $IMAGE_NAME:$TAG"
echo "Preserve data: $PRESERVE_DATA"
echo "Note: Using direct template embedding approach to ensure JavaScript is loaded"

# Check for required files
echo "Checking required files..."
if [ ! -f "Dockerfile" ]; then
  echo "Error: Dockerfile not found"
  exit 1
fi

if [ ! -d "custom/templates" ] || [ ! -f "custom/templates/view_file.tmpl" ]; then
  echo "Error: Custom templates directory not found or incomplete"
  exit 1
fi

if [ ! -d "custom/js" ] || [ ! -f "custom/js/dataset-preview.js" ]; then
  echo "Error: Custom JS directory not found or incomplete"
  exit 1
fi

# Stop containers but preserve volumes if requested
echo "Stopping any existing containers..."
if [ "$PRESERVE_DATA" = "yes" ]; then
  docker-compose down 2>/dev/null || true
else
  echo "WARNING: Data will not be preserved!"
  docker-compose down -v 2>/dev/null || true
  
  # Prune volumes and check for any other related images
  echo "Pruning unused volumes..."
  docker volume prune -f 2>/dev/null || true
fi

# Ensure all related containers are stopped
echo "Stopping any other containers using the image..."
docker ps -q --filter "ancestor=$IMAGE_NAME:$TAG" | xargs -r docker stop 2>/dev/null || true
docker ps -a -q --filter "ancestor=$IMAGE_NAME:$TAG" | xargs -r docker rm 2>/dev/null || true

# Remove the image
echo "Removing existing image if it exists..."
docker rmi "$IMAGE_NAME:$TAG" 2>/dev/null || true

# Check for any other images with the same name
echo "Checking for other images with the same name..."
docker images | grep "$IMAGE_NAME" | awk '{print $1":"$2}' | xargs -r docker rmi 2>/dev/null || true

# Build the Docker image
echo "Building image with no cache..."
DOCKER_BUILDKIT=1 docker build --no-cache --pull \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t "$IMAGE_NAME:$TAG" .
echo "Build complete!"

# Verify the image was built correctly
echo "Verifying image..."
if ! docker images | grep -q "$IMAGE_NAME"; then
  echo "Error: Image build failed or image not found"
  exit 1
fi
echo "Image verification successful"

# Push to registry if requested
if [ "$PUSH" = "yes" ]; then
  echo "Pushing to Docker registry..."
  docker push "$IMAGE_NAME:$TAG"
  echo "Push complete!"
fi

# Start for local testing
echo "Starting services..."
docker-compose up -d

echo ""
echo "Gitea should now be running at http://localhost:3000"
echo ""
echo "For server deployment with preserved data:"
echo "  ./build.sh goranlr/robotea latest yes yes"
echo ""
echo "For server deployment with clean data (will erase all repos and users):"
echo "  ./build.sh goranlr/robotea latest yes no"
echo ""
echo "Check the logs with: docker logs -f \$(docker-compose ps -q gitea)"
echo ""
echo "Note: This build directly embeds the JavaScript in the view_file.tmpl template"
echo "You should see a red indicator box saying 'Parquet JS Loaded' if JavaScript is working correctly."