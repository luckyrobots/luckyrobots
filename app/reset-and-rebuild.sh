#!/bin/bash
set -e

echo "==========================================================="
echo "  🔥 NUCLEAR OPTION - COMPLETE REBUILD & RESET 🔥"
echo "==========================================================="
echo "This script will:"
echo "1. Stop all containers"
echo "2. Remove ALL volumes"
echo "3. Rebuild the image from scratch"
echo "4. Start fresh services"
echo
echo "⚠️ WARNING: This will DELETE ALL YOUR DATA! ⚠️"
echo "Press Ctrl+C now to abort, or wait 5 seconds to continue..."
echo

sleep 5

echo "Starting nuclear reset..."

# Stop any running containers
echo "Stopping containers..."
docker-compose down -v || true

# Remove all Docker volumes that match our pattern
echo "Removing all volumes..."
docker volume ls | grep "gitea_" | awk '{print $2}' | xargs -r docker volume rm || true
docker volume prune -f

# Build image with no cache
echo "Rebuilding image with no cache..."
DOCKER_BUILDKIT=1 docker build --no-cache --pull \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t goranlr/robotea:latest .
echo "Build complete!"

# Start fresh services
echo "Starting services..."
docker-compose up -d

echo 
echo "==========================================================="
echo "  🎉 REBUILD COMPLETE - CHECK YOUR BROWSER 🎉"
echo "==========================================================="
echo
echo "If this doesn't fix the issue, we have more drastic options to try." 