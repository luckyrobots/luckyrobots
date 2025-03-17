FROM gitea/gitea:1.23.4

# Copy our customized view_file.tmpl and custom JS files
# Gitea looks for custom templates in /data/gitea/templates first, then /app/gitea/custom/templates
COPY custom/templates/view_file.tmpl /app/gitea/custom/templates/repo/view_file.tmpl
COPY custom/templates/home.tmpl /app/gitea/custom/templates/home.tmpl
COPY custom/templates/base/footer.tmpl /app/gitea/custom/templates/base/footer.tmpl
COPY custom/templates/base/footer_content.tmpl /app/gitea/custom/templates/base/footer_content.tmpl
COPY custom/templates/custom/extra_links_footer.tmpl /app/gitea/custom/templates/custom/extra_links_footer.tmpl
COPY custom/js/dataset-preview.js /app/gitea/custom/public/assets/js/dataset-preview.js

# Copy logo files to override Gitea defaults
COPY custom/logo/Logo.svg /app/gitea/custom/public/assets/img/logo.svg
COPY custom/logo/Logo.png /app/gitea/custom/public/assets/img/logo.png
COPY custom/logo/favicon.svg /app/gitea/custom/public/assets/img/favicon.svg
COPY custom/logo/favicon.png /app/gitea/custom/public/assets/img/favicon.png
COPY custom/logo/avatar_default.png /app/gitea/custom/public/assets/img/avatar_default.png
COPY custom/logo/Logo.png /app/gitea/custom/public/assets/img/apple-touch-icon.png

# Also copy favicon to root public directory with lowercase names for better browser compatibility
COPY custom/logo/favicon.png /app/gitea/custom/public/favicon.png
COPY custom/logo/favicon.svg /app/gitea/custom/public/favicon.svg

USER root

# Create necessary data directories and set permissions
RUN mkdir -p /data/gitea /app/gitea/data && \
    chown -R git:git /data /app/gitea && \
    chmod -R 755 /data /app/gitea

# Add custom translation file for update_mirrors
RUN mkdir -p /app/gitea/custom/options/locale/locale_en-US/ && \
    echo '[admin.dashboard]' > /app/gitea/custom/options/locale/locale_en-US/app.ini && \
    echo 'update_mirrors = Update Mirrors' >> /app/gitea/custom/options/locale/locale_en-US/app.ini

# Configure custom MIME type handler for Parquet files
RUN mkdir -p /app/gitea/custom/conf && \
    echo '[repository]' > /app/gitea/custom/conf/app.ini && \
    echo 'PREFER_INTERPRET_MEDIA_AS_TEXT = false' >> /app/gitea/custom/conf/app.ini && \
    echo '' >> /app/gitea/custom/conf/app.ini && \
    echo '[repository.mime]' >> /app/gitea/custom/conf/app.ini && \
    echo 'ENABLED = true' >> /app/gitea/custom/conf/app.ini && \
    echo '' >> /app/gitea/custom/conf/app.ini && \
    echo '[mime]' >> /app/gitea/custom/conf/app.ini && \
    echo 'TYPES_ORDER = application/vnd.apache.parquet' >> /app/gitea/custom/conf/app.ini && \
    echo 'TYPE.parquet = application/vnd.apache.parquet' >> /app/gitea/custom/conf/app.ini

# Add MIME type mapping to the server configuration
RUN mkdir -p /data/gitea/conf && \
    echo '[database]' > /data/gitea/conf/app.ini && \
    echo 'DB_TYPE = postgres' >> /data/gitea/conf/app.ini && \
    echo 'HOST = postgres:5432' >> /data/gitea/conf/app.ini && \
    echo 'NAME = gitea' >> /data/gitea/conf/app.ini && \
    echo 'USER = gitea' >> /data/gitea/conf/app.ini && \
    echo 'PASSWD = gitea' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[repository]' >> /data/gitea/conf/app.ini && \
    echo 'ROOT = /data/git/repositories' >> /data/gitea/conf/app.ini && \
    echo 'PREFER_INTERPRET_MEDIA_AS_TEXT = false' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[repository.mime]' >> /data/gitea/conf/app.ini && \
    echo 'ENABLED = true' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[mime]' >> /data/gitea/conf/app.ini && \
    echo 'TYPES_ORDER = application/vnd.apache.parquet' >> /data/gitea/conf/app.ini && \
    echo 'TYPE.parquet = application/vnd.apache.parquet' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[server]' >> /data/gitea/conf/app.ini && \
    echo 'APP_DATA_PATH = /data/gitea' >> /data/gitea/conf/app.ini && \
    echo 'STATIC_URL_PREFIX = /' >> /data/gitea/conf/app.ini && \
    echo 'OFFLINE_MODE = false' >> /data/gitea/conf/app.ini && \
    echo 'DOMAIN = localhost' >> /data/gitea/conf/app.ini && \
    echo 'ROOT_URL = http://localhost:3000/' >> /data/gitea/conf/app.ini && \
    echo 'HTTP_PORT = 3000' >> /data/gitea/conf/app.ini && \
    echo 'DISABLE_SSH = false' >> /data/gitea/conf/app.ini && \
    echo 'START_SSH_SERVER = true' >> /data/gitea/conf/app.ini && \
    echo 'SSH_DOMAIN = none' >> /data/gitea/conf/app.ini && \
    echo 'LFS_START_SERVER = true' >> /data/gitea/conf/app.ini && \ 
    echo 'LFS_CONTENT_PATH = /data/gitea/lfs' >> /data/gitea/conf/app.ini && \
    echo 'LFS_JWT_SECRET = ${HCLOUD_TOKEN}' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[repository.mimetype.mapping]' >> /data/gitea/conf/app.ini && \
    echo '.parquet=application/vnd.apache.parquet' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[ui]' >> /data/gitea/conf/app.ini && \
    echo 'DEFAULT_THEME = gitea-auto' >> /data/gitea/conf/app.ini && \
    echo 'THEMES = gitea,gitea-dark,gitea-auto' >> /data/gitea/conf/app.ini && \
    echo 'MAX_DISPLAY_FILE_SIZE = 8388608' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[security]' >> /data/gitea/conf/app.ini && \
    echo 'INSTALL_LOCK = true' >> /data/gitea/conf/app.ini && \
    echo 'SECRET_KEY = $(openssl rand -base64 32)' >> /data/gitea/conf/app.ini && \
    echo 'INTERNAL_TOKEN = $(openssl rand -base64 64)' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[service]' >> /data/gitea/conf/app.ini && \
    echo 'DISABLE_REGISTRATION = false' >> /data/gitea/conf/app.ini && \
    echo 'REQUIRE_SIGNIN_VIEW = false' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[ssh]' >> /data/gitea/conf/app.ini && \
    echo 'DISABLE_AUTHORIZED_KEYS_BACKUP = true' >> /data/gitea/conf/app.ini && \
    echo 'CREATE_AUTHORIZED_KEYS_FILE = false' >> /data/gitea/conf/app.ini && \
    echo 'MINIMUM_KEY_SIZE = 0' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[log]' >> /data/gitea/conf/app.ini && \
    echo 'LEVEL = info' >> /data/gitea/conf/app.ini && \
    echo 'ROOT_PATH = /data/gitea/log' >> /data/gitea/conf/app.ini && \
    echo '' >> /data/gitea/conf/app.ini && \
    echo '[indexer]' >> /data/gitea/conf/app.ini && \
    echo 'ISSUE_INDEXER_PATH = /data/gitea/indexers/issues.bleve' >> /data/gitea/conf/app.ini && \
    echo 'REPO_INDEXER_PATH = /data/gitea/indexers/repos.bleve' >> /data/gitea/conf/app.ini && \
    chmod 644 /data/gitea/conf/app.ini && \
    chown -R git:git /data/gitea/conf

# Create header and footer templates with diagnostic javascript
RUN mkdir -p /app/gitea/custom/templates/custom && \
    echo '<script>' > /app/gitea/custom/templates/custom/header.tmpl && \
    echo 'console.log("Custom header script loaded");' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '// Override SSH key functionality' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo 'if (window.addEventListener) {' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '  window.addEventListener("load", function() {' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    // Hide SSH key sections' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    const style = document.createElement("style");' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    style.textContent = `.ssh-key-section, .ui.ssh.list, .ssh-key-add { display: none !important; }`;' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    document.head.append(style);' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    console.log("SSH key sections hidden");' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    ' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    // Force favicon refresh' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    const faviconLink = document.createElement("link");' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    faviconLink.rel = "shortcut icon";' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    faviconLink.href = "/favicon.png?v=" + new Date().getTime();' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    document.head.appendChild(faviconLink);' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '    console.log("Custom favicon link added");' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '  });' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '}' >> /app/gitea/custom/templates/custom/header.tmpl && \
    echo '</script>' >> /app/gitea/custom/templates/custom/header.tmpl

# Create a footer with diagnostic script and dataset-preview.js
RUN mkdir -p /app/gitea/custom/templates/custom && \
    echo '<script type="text/javascript">' > /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '// This is a diagnostic script to confirm JavaScript execution' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo 'console.log("DIAGNOSTIC: Footer script is being loaded!");' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '// Create a visual indicator that the script is running' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo 'document.addEventListener("DOMContentLoaded", function() {' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  console.log("DIAGNOSTIC: DOM is ready, adding indicator");' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  ' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  // Create a notification element' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  var notificationDiv = document.createElement("div");' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.position = "fixed";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.bottom = "20px";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.right = "20px";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.backgroundColor = "#4caf50";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.color = "white";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.padding = "10px";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.borderRadius = "5px";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.style.zIndex = "9999";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  notificationDiv.textContent = "JavaScript is running!";' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '  document.body.appendChild(notificationDiv);' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '});' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '</script>' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '<!-- Now include the dataset-preview.js content directly -->' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '<script type="text/javascript">' >> /app/gitea/custom/templates/custom/footer.tmpl && \
    cat /app/gitea/custom/public/assets/js/dataset-preview.js >> /app/gitea/custom/templates/custom/footer.tmpl && \
    echo '</script>' >> /app/gitea/custom/templates/custom/footer.tmpl

# Copy the dataset-preview.js to the correct public assets location
# According to Gitea docs, static files should be in /app/gitea/public/assets/js
RUN mkdir -p /app/gitea/public/assets/js && \
    cp /app/gitea/custom/public/assets/js/dataset-preview.js /app/gitea/public/assets/js/ && \
    chmod -R 755 /app/gitea/public && \
    chown -R git:git /app/gitea/public

# Also place the JavaScript file in the GITEA_CUSTOM directory structure
# This is critical for remote deployments where GITEA_CUSTOM=/data/gitea
RUN mkdir -p /data/gitea/public/assets/js/ && \
    cp /app/gitea/custom/public/assets/js/dataset-preview.js /data/gitea/public/assets/js/ && \
    chmod -R 755 /data/gitea/public && \
    chown -R git:git /data/gitea/public

# Create a new view_file.tmpl with embedded JavaScript
RUN cp /app/gitea/custom/templates/repo/view_file.tmpl /app/gitea/custom/templates/repo/view_file.tmpl.orig && \
    grep -v '<script type="application/javascript" src="/assets/js/dataset-preview.js"></script>' /app/gitea/custom/templates/repo/view_file.tmpl.orig > /app/gitea/custom/templates/repo/view_file.tmpl && \
    echo '<script type="text/javascript">' >> /app/gitea/custom/templates/repo/view_file.tmpl && \
    echo '// Embedded dataset-preview.js to avoid 404 errors' >> /app/gitea/custom/templates/repo/view_file.tmpl && \
    cat /app/gitea/custom/public/assets/js/dataset-preview.js >> /app/gitea/custom/templates/repo/view_file.tmpl && \
    echo '</script>' >> /app/gitea/custom/templates/repo/view_file.tmpl

# Also add a direct HTML marker to verify template loading
RUN sed -i '/<div class="non-diff-file-content">/ a\<div style="background-color: yellow; color: black; padding: 5px; margin: 5px; border: 1px solid black;">CUSTOM TEMPLATE LOADED</div>' /app/gitea/custom/templates/repo/view_file.tmpl

# Also place the template in the data directory to ensure it's found
RUN mkdir -p /data/gitea/templates/repo && \
    cp /app/gitea/custom/templates/repo/view_file.tmpl /data/gitea/templates/repo/ && \
    mkdir -p /data/gitea/templates/base && \
    cp /app/gitea/custom/templates/base/footer.tmpl /data/gitea/templates/base/ && \
    cp /app/gitea/custom/templates/base/footer_content.tmpl /data/gitea/templates/base/ && \
    mkdir -p /data/gitea/templates/custom && \
    cp /app/gitea/custom/templates/custom/extra_links_footer.tmpl /data/gitea/templates/custom/ && \
    cp /app/gitea/custom/templates/home.tmpl /data/gitea/templates/ && \
    chown -R git:git /data/gitea/templates

# Create a default admin user
RUN mkdir -p /data/gitea/db && \
    chown -R git:git /data/gitea/db

# Create a startup script that fixes permissions and creates the admin user
RUN echo '#!/bin/bash' > /usr/local/bin/gitea-start.sh && \
    echo 'mkdir -p /data/git/.ssh /data/gitea/data /app/gitea/data /data/gitea/templates/repo' >> /usr/local/bin/gitea-start.sh && \
    echo 'touch /data/git/.ssh/authorized_keys /data/git/.ssh/authorized_keys.tmp' >> /usr/local/bin/gitea-start.sh && \
    echo 'chmod -R 777 /data /app/gitea/data' >> /usr/local/bin/gitea-start.sh && \
    echo 'chown -R git:git /data /app/gitea/data' >> /usr/local/bin/gitea-start.sh && \
    echo 'chmod 777 /data/git/.ssh/authorized_keys.tmp' >> /usr/local/bin/gitea-start.sh && \
    echo 'chmod 777 /data/git/.ssh/authorized_keys' >> /usr/local/bin/gitea-start.sh && \
    echo '# Ensure the template is in both locations' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/templates/repo/view_file.tmpl /data/gitea/templates/repo/' >> /usr/local/bin/gitea-start.sh && \
    echo 'mkdir -p /data/gitea/templates/base' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/templates/base/footer.tmpl /data/gitea/templates/base/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/templates/base/footer_content.tmpl /data/gitea/templates/base/' >> /usr/local/bin/gitea-start.sh && \
    echo 'mkdir -p /data/gitea/templates/custom' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/templates/custom/extra_links_footer.tmpl /data/gitea/templates/custom/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/templates/home.tmpl /data/gitea/templates/' >> /usr/local/bin/gitea-start.sh && \
    echo 'chown -R git:git /data/gitea/templates' >> /usr/local/bin/gitea-start.sh && \
    echo '# Ensure the JavaScript file is in the correct location for GITEA_CUSTOM' >> /usr/local/bin/gitea-start.sh && \
    echo 'mkdir -p /data/gitea/public/assets/js/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/assets/js/dataset-preview.js /data/gitea/public/assets/js/' >> /usr/local/bin/gitea-start.sh && \
    echo 'chmod -R 755 /data/gitea/public' >> /usr/local/bin/gitea-start.sh && \
    echo 'chown -R git:git /data/gitea/public' >> /usr/local/bin/gitea-start.sh && \
    echo '# Copy logo files to the data directory' >> /usr/local/bin/gitea-start.sh && \
    echo 'mkdir -p /data/gitea/public/assets/img/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/assets/img/logo.svg /data/gitea/public/assets/img/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/assets/img/logo.png /data/gitea/public/assets/img/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/assets/img/favicon.svg /data/gitea/public/assets/img/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/assets/img/favicon.png /data/gitea/public/assets/img/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/assets/img/avatar_default.png /data/gitea/public/assets/img/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/assets/img/apple-touch-icon.png /data/gitea/public/assets/img/' >> /usr/local/bin/gitea-start.sh && \
    echo 'chmod -R 755 /data/gitea/public/assets/img' >> /usr/local/bin/gitea-start.sh && \
    echo 'chown -R git:git /data/gitea/public/assets/img' >> /usr/local/bin/gitea-start.sh && \
    echo '# Also copy favicon to root public directory for better browser compatibility' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/favicon.png /data/gitea/public/' >> /usr/local/bin/gitea-start.sh && \
    echo 'cp -f /app/gitea/custom/public/favicon.svg /data/gitea/public/' >> /usr/local/bin/gitea-start.sh && \
    echo 'chmod 644 /data/gitea/public/favicon.png /data/gitea/public/favicon.svg' >> /usr/local/bin/gitea-start.sh && \
    echo 'chown -R git:git /data/gitea/public' >> /usr/local/bin/gitea-start.sh && \
    echo '' >> /usr/local/bin/gitea-start.sh && \
    echo '# Remove any existing setup_complete flag to force admin user creation' >> /usr/local/bin/gitea-start.sh && \
    echo 'rm -f /data/gitea/.setup_complete' >> /usr/local/bin/gitea-start.sh && \
    echo '' >> /usr/local/bin/gitea-start.sh && \
    echo '# Remove any existing SQLite database to force PostgreSQL usage' >> /usr/local/bin/gitea-start.sh && \
    echo 'rm -f /data/gitea/gitea.db' >> /usr/local/bin/gitea-start.sh && \
    echo '' >> /usr/local/bin/gitea-start.sh && \
    echo '# Check if admin user exists, if not create it' >> /usr/local/bin/gitea-start.sh && \
    echo 'if [ ! -f "/data/gitea/.setup_complete" ]; then' >> /usr/local/bin/gitea-start.sh && \
    echo '  echo "First run, setting up admin user..."' >> /usr/local/bin/gitea-start.sh && \
    echo '  # Start Gitea in the background' >> /usr/local/bin/gitea-start.sh && \
    echo '  su git -c "GITEA__database__DB_TYPE=postgres GITEA__database__HOST=postgres:5432 GITEA__database__NAME=gitea GITEA__database__USER=gitea GITEA__database__PASSWD=gitea /app/gitea/gitea web" &' >> /usr/local/bin/gitea-start.sh && \
    echo '  # Wait for Gitea to start' >> /usr/local/bin/gitea-start.sh && \
    echo '  sleep 15' >> /usr/local/bin/gitea-start.sh && \
    echo '  # Create admin user with environment variables or defaults' >> /usr/local/bin/gitea-start.sh && \
    echo '  ADMIN_USER=${GITEA_ADMIN_USERNAME:-admin}' >> /usr/local/bin/gitea-start.sh && \
    echo '  ADMIN_PASSWORD=${GITEA_ADMIN_PASSWORD:-admin123}' >> /usr/local/bin/gitea-start.sh && \
    echo '  ADMIN_EMAIL=${GITEA_ADMIN_EMAIL:-admin@example.com}' >> /usr/local/bin/gitea-start.sh && \
    echo '  echo "Creating admin user: $ADMIN_USER"' >> /usr/local/bin/gitea-start.sh && \
    echo '  su git -c "GITEA__database__DB_TYPE=postgres GITEA__database__HOST=postgres:5432 GITEA__database__NAME=gitea GITEA__database__USER=gitea GITEA__database__PASSWD=gitea /app/gitea/gitea admin user create --username $ADMIN_USER --password $ADMIN_PASSWORD --email $ADMIN_EMAIL --admin"' >> /usr/local/bin/gitea-start.sh && \
    echo '  # Mark setup as complete' >> /usr/local/bin/gitea-start.sh && \
    echo '  touch /data/gitea/.setup_complete' >> /usr/local/bin/gitea-start.sh && \
    echo '  # Stop the background Gitea process' >> /usr/local/bin/gitea-start.sh && \
    echo '  pkill gitea || true' >> /usr/local/bin/gitea-start.sh && \
    echo '  sleep 5' >> /usr/local/bin/gitea-start.sh && \
    echo 'fi' >> /usr/local/bin/gitea-start.sh && \
    echo '' >> /usr/local/bin/gitea-start.sh && \
    echo 'echo "Starting Gitea..."' >> /usr/local/bin/gitea-start.sh && \
    echo 'su git -c "GITEA__database__DB_TYPE=postgres GITEA__database__HOST=postgres:5432 GITEA__database__NAME=gitea GITEA__database__USER=gitea GITEA__database__PASSWD=gitea /app/gitea/gitea web" || GITEA__database__DB_TYPE=postgres GITEA__database__HOST=postgres:5432 GITEA__database__NAME=gitea GITEA__database__USER=gitea GITEA__database__PASSWD=gitea /app/gitea/gitea web' >> /usr/local/bin/gitea-start.sh && \
    chmod +x /usr/local/bin/gitea-start.sh

# Configure the app with environment variables
ENV GITEA__server__DISABLE_SSH=false \
    GITEA__server__START_SSH_SERVER=true \
    GITEA__server__OFFLINE_MODE=false \
    GITEA__server__APP_DATA_PATH=/data/gitea \
    GITEA__ssh__DISABLE_AUTHORIZED_KEYS_BACKUP=true \
    GITEA__ssh__CREATE_AUTHORIZED_KEYS_FILE=false \
    GITEA__ssh__MINIMUM_KEY_SIZE=0 \
    GITEA__repository__PREFER_INTERPRET_MEDIA_AS_TEXT=false \
    GITEA__repository.mime__ENABLED=true \
    GITEA__mime__TYPES_ORDER="application/vnd.apache.parquet" \
    GITEA__mime__TYPE.parquet="application/vnd.apache.parquet" \
    GITEA__repository.mimetype.mapping__PARQUET="application/vnd.apache.parquet" \
    GITEA__ui__MAX_DISPLAY_FILE_SIZE="8388608" \
    GITEA__ui__DEFAULT_THEME="gitea-auto" \
    GITEA__database__DB_TYPE="postgres" \
    GITEA__database__HOST="postgres:5432" \
    GITEA__database__NAME="gitea" \
    GITEA__database__USER="gitea" \
    GITEA__database__PASSWD="gitea" \
    GITEA__security__INSTALL_LOCK=true \
    # Actions configuration
    GITEA__actions__ENABLED=true \
    GITEA__actions__DEFAULT_ACTIONS_URL="https://github.com" \
    GITEA__actions__STORAGE_PATH=/data/gitea/actions \
    GITEA__actions__QUEUE_TYPE=level \
    GITEA__actions__QUEUE_CONN_STR=/data/gitea/actions_queue \
    GITEA__actions__CLEANUP_ENABLED=true \
    GITEA__actions__CLEANUP_INTERVAL=24h \
    GITEA__actions__CLEANUP_EXPIRED_ARTIFACTS_AFTER=24h \
    GITEA__actions__CLEANUP_EXPIRED_RUNS_AFTER=168h

# Set up runner directories and configuration
RUN mkdir -p /data/gitea/runner && \
    chown -R git:git /data/gitea/runner && \
    chmod -R 755 /data/gitea/runner

# Add runner initialization to startup script
RUN sed -i '/# Check if admin user exists/i \
# Initialize runner directory and configuration\n\
mkdir -p /data/gitea/runner\n\
chown -R git:git /data/gitea/runner\n\
chmod -R 755 /data/gitea/runner\n\
\n\
chown -R git:git /data/gitea/runner/.gitea\n\
\n\
# Add retry logic for runner registration\n\
for i in {1..5}; do\n\
  if [ -n "$GITEA_RUNNER_REGISTRATION_TOKEN" ]; then\n\
    echo "Attempting to register runner (attempt $i)..."\n\
    su git -c "cd /data/gitea/runner && /usr/local/bin/act_runner register --no-interactive --instance http://gitea:3000 --token $GITEA_RUNNER_REGISTRATION_TOKEN" && break\n\
    sleep 5\n\
  fi\n\
done\n\' /usr/local/bin/gitea-start.sh

# Stay as root user
USER root
ENTRYPOINT ["/usr/local/bin/gitea-start.sh"]