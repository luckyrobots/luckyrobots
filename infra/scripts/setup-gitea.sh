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

# Dynamically find the Hetzner Cloud volume mount point
HC_VOLUME_PATH=$(mount | grep -E 'HC_Volume|gitea-storage' | awk '{print $3}' | head -n 1)
if [ -z "$HC_VOLUME_PATH" ]; then
  log_safe "WARNING: Could not find Hetzner Cloud volume mount. Falling back to /mnt/gitea-storage"
  HC_VOLUME_PATH="/mnt/gitea-storage"
fi

log_safe "Using Hetzner Cloud volume mounted at: $HC_VOLUME_PATH"

# Create subdirectories on the volume for different services
log_safe "Creating subdirectories on the volume..."
mkdir -p $HC_VOLUME_PATH/postgres
mkdir -p $HC_VOLUME_PATH/gitea
mkdir -p $HC_VOLUME_PATH/runner
mkdir -p $HC_VOLUME_PATH/repositories

# Set proper permissions
chown -R 1000:1000 $HC_VOLUME_PATH

log_safe "Preparing app.ini configuration for volume..."
mkdir -p ${HC_VOLUME_PATH}/gitea/gitea/conf/

# Setup Caddy
mkdir -p /opt/gitea/caddy/data
mkdir -p /opt/gitea/caddy/config

# Create the Caddyfile
cat > /opt/gitea/caddy/Caddyfile << EOF
app.luckyrobots.ai {
    reverse_proxy gitea:3000
    tls {
        protocols tls1.2 tls1.3
    }
    log {
        output file /data/logs/access.log {
            roll_size 10MB
            roll_keep 10
        }
    }
}
EOF

# Create the app.ini file based on known settings from the Dockerfile
cat > ${HC_VOLUME_PATH}/gitea/gitea/conf/app.ini << EOF
[database]
DB_TYPE = postgres
HOST = postgres:5432
NAME = gitea
USER = gitea
PASSWD = gitea

[repository]
ROOT = /data/git/repositories
PREFER_INTERPRET_MEDIA_AS_TEXT = false

[repository.mime]
ENABLED = true

[mime]
TYPES_ORDER = application/vnd.apache.parquet
TYPE.parquet = application/vnd.apache.parquet

[server]
APP_DATA_PATH = /data/gitea
STATIC_URL_PREFIX = /
OFFLINE_MODE = false
DOMAIN = app.luckyrobots.ai
ROOT_URL = https://app.luckyrobots.ai/
HTTP_PORT = 3000
DISABLE_SSH = false
START_SSH_SERVER = true
SSH_DOMAIN = app.luckyrobots.ai

[repository.mimetype.mapping]
.parquet=application/vnd.apache.parquet

[ui]
DEFAULT_THEME = gitea-auto
THEMES = gitea,gitea-dark,gitea-auto
MAX_DISPLAY_FILE_SIZE = 8388608

[security]
INSTALL_LOCK = true
SECRET_KEY = $(openssl rand -base64 32)
INTERNAL_TOKEN = $(openssl rand -base64 64)

[service]
DISABLE_REGISTRATION = false
REQUIRE_SIGNIN_VIEW = false

[ssh]
DISABLE_AUTHORIZED_KEYS_BACKUP = true
CREATE_AUTHORIZED_KEYS_FILE = false
MINIMUM_KEY_SIZE = 0

[log]
LEVEL = info
ROOT_PATH = /data/gitea/log

[indexer]
ISSUE_INDEXER_PATH = /data/gitea/indexers/issues.bleve
REPO_INDEXER_PATH = /data/gitea/indexers/repos.bleve
EOF

# Set proper permissions
log_safe "Setting permissions on configuration files..."
chmod 644 ${HC_VOLUME_PATH}/gitea/gitea/conf/app.ini
chown -R 1000:1000 ${HC_VOLUME_PATH}/gitea

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
      - ${HC_VOLUME_PATH}/postgres:/var/lib/postgresql/data
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
      - "2222:22"
    volumes:
      - ${HC_VOLUME_PATH}/gitea:/data
      - ${HC_VOLUME_PATH}/repositories:/data/git/repositories
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
      - GITEA__server__DISABLE_SSH=false
      - GITEA__server__START_SSH_SERVER=true
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
      # Crucial networking settings
      - GITEA__server__DOMAIN=app.luckyrobots.ai
      - GITEA__server__ROOT_URL=https://app.luckyrobots.ai/
      - GITEA__server__OFFLINE_MODE=false
      - GITEA__server__LOCAL_ROOT_URL=http://gitea:3000/
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
      start_period: 15s

  caddy:
    image: caddy:2-alpine
    restart: always
    depends_on:
      - gitea
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /opt/gitea/caddy/Caddyfile:/etc/caddy/Caddyfile
      - /opt/gitea/caddy/data:/data
      - /opt/gitea/caddy/config:/config
    networks:
      - gitea

  runner:
    image: gitea/act_runner:latest
    restart: unless-stopped
    init: true
    depends_on:
      gitea:
        condition: service_healthy
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ${HC_VOLUME_PATH}/runner:/data
    networks:
      - gitea
    environment:
      - GITEA_INSTANCE_URL=http://gitea:3000
      - GITEA_RUNNER_REGISTRATION_TOKEN=${GITEA_RUNNER_REGISTRATION_TOKEN:-}
      - GITEA_RUNNER_NAME=docker-runner
      - GITEA_RUNNER_LABELS=ubuntu-latest:docker://node:16-bullseye,ubuntu-22.04:docker://node:16-bullseye
      - DOCKER_HOST=unix:///var/run/docker.sock
    healthcheck:
      test: ["CMD", "ps", "aux"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    extra_hosts:
      - "host.docker.internal:host-gateway"
    deploy:
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s

networks:
  gitea:
    name: gitea_network
    # Explicitly use bridge to ensure proper container communication
    driver: bridge
EOF

# Create logs directory for Caddy
mkdir -p /opt/gitea/caddy/data/logs
chmod -R 755 /opt/gitea/caddy

log_safe "Docker Compose configuration created, using volume at: $HC_VOLUME_PATH"

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

# First check if the API endpoint works, which indicates successful installation
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/v1/version)
log_safe "API status: $API_STATUS"

if [ "$API_STATUS" -eq 200 ]; then
  log_safe "Gitea is already installed and API is working"
else
  log_safe "Gitea needs installation. Performing installation..."
  
  # Try to install via the API
  log_safe "Installing Gitea via API..."
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
  log_safe "Installation result: $INSTALL_RESULT"
  log_safe "Installation status code: $INSTALL_STATUS"
  
  # Wait for Gitea to restart after installation
  log_safe "Waiting for Gitea to restart after installation..."
  sleep 20
  
  # Try connecting to the API endpoint again to confirm installation worked
  API_STATUS_AFTER=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/v1/version)
  log_safe "API status after installation: $API_STATUS_AFTER"
  
  if [ "$API_STATUS_AFTER" -ne 200 ]; then
    log_safe "WARNING: Gitea installation may not have succeeded. Will attempt to proceed anyway."
  fi
fi

# Create a new access token
log_safe "Creating admin access token..."
GITEA_TOKEN_RESULT=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"name":"admin-token","scopes":["admin"]}' \
  -u "${GITEA_ADMIN_USERNAME}:${GITEA_ADMIN_PASSWORD}" \
  http://localhost:3000/api/v1/users/${GITEA_ADMIN_USERNAME}/tokens | jq -r '.sha1')

if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
  log_safe "Successfully created access token"


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