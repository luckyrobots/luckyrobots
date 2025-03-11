#!/bin/bash
# Enable error trace but preserve sensitive data
set -e

# Function to log safely (without revealing sensitive data)
log_safe() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Get arguments from Terraform
GITEA_ADMIN_USERNAME="$1"
GITEA_ADMIN_PASSWORD="$2"  # Use the actual password for Docker Compose
GITEA_ADMIN_EMAIL="$3"
# Store original password for logging safety - display REDACTED in logs
DISPLAY_PASSWORD="REDACTED"

log_safe "Starting Gitea setup with user: $GITEA_ADMIN_USERNAME and email: $GITEA_ADMIN_EMAIL"
log_safe "Running on: $(uname -a)"
log_safe "Working directory: $(pwd)"

# Install dependencies
log_safe "Installing dependencies..."
sudo apt update && sudo apt install -y docker.io debian-keyring debian-archive-keyring apt-transport-https curl jq || {
  log_safe "Failed to install dependencies"
  exit 1
}

log_safe "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
log_safe "Docker Compose version: $(docker-compose --version)"

# Make sure Docker is running
log_safe "Ensuring Docker is running..."
sudo systemctl enable docker
sudo systemctl start docker
docker_status=$(sudo systemctl is-active docker)
log_safe "Docker status: $docker_status"

# Create directories with proper permissions
log_safe "Creating data directories with proper permissions..."
sudo mkdir -p /opt/gitea/data
sudo chown -R 1000:1000 /opt/gitea  # Set ownership to expected UID:GID

# Create docker-compose.yml
log_safe "Creating Docker Compose configuration..."
cat << EOF > /opt/gitea/docker-compose.yml
version: '3'

services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-gitea}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-gitea}
      - POSTGRES_DB=${POSTGRES_DB:-gitea}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - gitea
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gitea"]
      interval: 10s
      timeout: 5s
      retries: 5

  gitea:
    image: goranlr/robotea:latest
    restart: always
    user: root
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "3000:3000"
    volumes:
      - gitea_data:/data
    networks:
      - gitea
    environment:
      - USER_UID=1000
      - USER_GID=1000
      # Admin user settings
      - GITEA_ADMIN_USERNAME=${GITEA_ADMIN_USERNAME:-admin}
      - GITEA_ADMIN_PASSWORD=${GITEA_ADMIN_PASSWORD:-admin123}
      - GITEA_ADMIN_EMAIL=${GITEA_ADMIN_EMAIL:-admin@example.com}
      # Database settings
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=postgres:5432
      - GITEA__database__NAME=${POSTGRES_DB:-gitea}
      - GITEA__database__USER=${POSTGRES_USER:-gitea}
      - GITEA__database__PASSWD=${POSTGRES_PASSWORD:-gitea}
      # Path settings
      - GITEA__server__APP_DATA_PATH=/data/gitea
      - GITEA__repository__ROOT=/data/git/repositories
      - GITEA_WORK_DIR=/data/gitea
      # SSH settings
      - GITEA__server__DISABLE_SSH=true
      - GITEA__server__START_SSH_SERVER=false
      - GITEA__ssh__DISABLE_AUTHORIZED_KEYS_BACKUP=true
      - GITEA__ssh__CREATE_AUTHORIZED_KEYS_FILE=false
      # MIME type settings for Parquet files
      - GITEA__repository__PREFER_INTERPRET_MEDIA_AS_TEXT=false
      - GITEA__repository.mime__ENABLED=true
      - GITEA__mime__TYPES_ORDER=application/vnd.apache.parquet
      - GITEA__mime__TYPE.parquet=application/vnd.apache.parquet
      - GITEA__repository.mimetype.mapping__PARQUET=application/vnd.apache.parquet
      # Server and static file serving
      - GITEA__server__STATIC_URL_PREFIX=/
      - GITEA__server__OFFLINE_MODE=false
      - GITEA__server__ROOT_URL=http://localhost:3000/
      - GITEA__server__LOCAL_ROOT_URL=http://localhost:3000/
      # Actions settings
      - GITEA__actions__ENABLED=true
      - GITEA__actions__DEFAULT_ACTIONS_URL=https://github.com
      - GITEA__actions__STORAGE_PATH=/data/gitea/actions
      - GITEA__actions__QUEUE_TYPE=level
      - GITEA__actions__QUEUE_CONN_STR=/data/gitea/actions_queue
      - GITEA__actions__CLEANUP_ENABLED=true
      - GITEA__actions__CLEANUP_INTERVAL=24h
      - GITEA__actions__CLEANUP_EXPIRED_ARTIFACTS_AFTER=24h
      - GITEA__actions__CLEANUP_EXPIRED_RUNS_AFTER=168h
      # Custom configuration for debugging
      - GITEA__log__LEVEL=debug
      - GITEA__log__ROUTER=console
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

  runner:
    image: gitea/act_runner:latest
    restart: unless-stopped
    init: true
    depends_on:
      gitea:
        condition: service_healthy
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - runner_data:/data
    networks:
      - gitea
    environment:
      - GITEA_INSTANCE_URL=http://gitea:3000
      - GITEA_RUNNER_REGISTRATION_TOKEN=${GITEA_RUNNER_REGISTRATION_TOKEN:-}
      - GITEA_RUNNER_NAME=docker-runner
      - GITEA_RUNNER_LABELS=ubuntu-latest:docker://node:16-bullseye,ubuntu-22.04:docker://node:16-bullseye
    healthcheck:
      test: ["CMD", "curl", "-f", "http://gitea:3000/api/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s

networks:
  gitea:
    name: gitea_network

volumes:
  postgres_data:
    name: gitea_postgres_data
  gitea_data:
    name: gitea_data
  runner_data:
    name: gitea_runner_data 
EOF

log_safe "Starting Gitea container..."
cd /opt/gitea
sudo docker-compose pull
sudo docker-compose down --remove-orphans || true
sudo docker-compose up -d

# Wait for Gitea to be ready
log_safe "Waiting for Gitea to be ready..."
max_retries=30
count=0
while [[ $count -lt $max_retries ]]; do
  if curl -s http://localhost:3000/ > /dev/null; then
    log_safe "Gitea is up and running!"
    break
  fi
  log_safe "Waiting for Gitea to start ($count/$max_retries)..."
  count=$((count+1))
  sleep 5
done

if [[ $count -ge $max_retries ]]; then
  log_safe "Gitea failed to start in time. Check container logs:"
  sudo docker logs robotea
  exit 1
fi

# Check if we need to run the installation
INSTALL_NEEDED=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/install)
log_safe "Install page status: $INSTALL_NEEDED"

if [ "$INSTALL_NEEDED" -eq 200 ]; then
  log_safe 'Setting up Gitea for the first time...'
 INSTALL_RESULT=$(curl -X POST http://localhost:3000/install \
    --data-urlencode "db_type=postgres" \
    --data-urlencode "db_host=postgres:5432" \
    --data-urlencode "db_name=gitea" \
    --data-urlencode "db_user=gitea" \
    --data-urlencode "db_passwd=gitea" \
    --data-urlencode "app_name=Lucky Robots" \
    --data-urlencode "repo_root_path=/data/git/repositories" \
    --data-urlencode "log_root_path=/data/gitea/log" \
    --data-urlencode "admin_name=${GITEA_ADMIN_USERNAME}" \
    --data-urlencode "admin_passwd=${GITEA_ADMIN_PASSWORD}" \
    --data-urlencode "admin_confirm_passwd=${GITEA_ADMIN_PASSWORD}" \
    --data-urlencode "admin_email=${GITEA_ADMIN_EMAIL}" 2>&1)
  
  INSTALL_STATUS=$?
  if [ $INSTALL_STATUS -ne 0 ]; then
    log_safe "Gitea installation failed with status $INSTALL_STATUS"
    log_safe "Error response: ${INSTALL_RESULT//password=*REDACTED*/password=REDACTED}"
    # Debug container issues
    log_safe "Container logs:"
    sudo docker logs robotea
    # Try to fix permissions again
    log_safe "Attempting to fix permissions..."
    sudo docker exec -u root robotea chown -R git:git /data
    exit 1
  fi
  
  log_safe 'Gitea installation completed'
  sleep 10
fi

# Create a new access token
log_safe 'Creating access token...'
GITEA_TOKEN_RESULT=$(curl -X POST -H 'Content-Type: application/json' \
  -d '{"name":"terraform-token"}' \
  -u "${GITEA_ADMIN_USERNAME}:${GITEA_ADMIN_PASSWORD}" \
  http://localhost:3000/api/v1/users/${GITEA_ADMIN_USERNAME}/tokens 2>&1)

GITEA_TOKEN=$(echo "$GITEA_TOKEN_RESULT" | jq -r '.sha1' 2>/dev/null)

# Create runner registration token
log_safe "Creating runner registration token..."
RUNNER_TOKEN=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  http://localhost:3000/api/v1/admin/runners/registration-token | jq -r '.token')

if [ -n "$RUNNER_TOKEN" ] && [ "$RUNNER_TOKEN" != "null" ]; then
  log_safe "Successfully created runner registration token: ${RUNNER_TOKEN:0:5}..."
  
  # Save the token to multiple locations to ensure it's found
  echo "GITEA_RUNNER_REGISTRATION_TOKEN=${RUNNER_TOKEN}" >> "$PROJECT_ROOT/.env"
  echo "export GITEA_RUNNER_REGISTRATION_TOKEN=\"${RUNNER_TOKEN}\"" >> /etc/profile.d/gitea-runner.sh
  chmod 644 /etc/profile.d/gitea-runner.sh
  
  # Also save to docker environment
  mkdir -p /etc/docker
  echo "{\"env\":[\"GITEA_RUNNER_REGISTRATION_TOKEN=${RUNNER_TOKEN}\"]}" > /etc/docker/daemon.json
  
  # Create a dedicated token file
  echo "${RUNNER_TOKEN}" > /opt/gitea/runner_token
  chmod 600 /opt/gitea/runner_token
  
  # Make sure Docker can access the environment variable
  systemctl daemon-reload
  systemctl restart docker
  
  # Export for current session
  export GITEA_RUNNER_REGISTRATION_TOKEN="${RUNNER_TOKEN}"
  
  # Verify the token is available
  log_safe "Verifying token is available..."
  if [ -z "$GITEA_RUNNER_REGISTRATION_TOKEN" ]; then
    log_safe "ERROR: Token is not available in the environment"
    env | grep -i token || true
  else
    log_safe "Token is available in the environment"
  fi
  
  # Start the runner with an explicit token reference
  log_safe "Starting runner with the token..."
  cd "$PROJECT_ROOT"
  GITEA_RUNNER_REGISTRATION_TOKEN="${RUNNER_TOKEN}" docker-compose up -d runner
  
  # Wait for runner to register
  log_safe "Waiting for runner to register..."
  sleep 20
  
  # Check runner logs to verify registration
  log_safe "Checking runner logs..."
  docker-compose logs runner | tail -n 20
  
  # Verify runner is registered by querying the API
  log_safe "Verifying runner registration via API..."
  RUNNER_COUNT=$(curl -s -H "Authorization: token ${GITEA_TOKEN}" \
    http://localhost:3000/api/v1/admin/runners | jq '. | length')
  log_safe "Number of registered runners: $RUNNER_COUNT"
else
  log_safe "Failed to create runner registration token"
  exit 1
fi

# Verify everything is working correctly
log_safe "Verifying Gitea deployment..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
GITEA_STATUS=$?

if [ $GITEA_STATUS -ne 0 ]; then
  log_safe "Warning: Gitea might not be running correctly."
  log_safe "Container logs:"
  sudo docker logs robotea
  exit 1
fi

log_safe "Gitea deployment complete and verified!"
log_safe "You can access Gitea at: http://SERVER_IP:3000/" 