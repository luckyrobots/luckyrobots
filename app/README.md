# Gitea Parquet Viewer

This repository contains a customized version of Gitea with built-in Parquet file viewing capabilities. It allows you to view and explore Parquet files directly in the Gitea web interface.

## Features

- Seamless integration with Gitea
- Browser-based Parquet file viewing without external dependencies
- Uses DuckDB WASM for efficient Parquet file parsing
- Displays metadata and table data for Parquet files
- Fallback to basic information when DuckDB is not available

## Using the Docker Image

### Option 1: Using Docker Run

```bash
docker run -d --name=gitea-parquet-viewer \
  -p 3000:3000 \
  -p 22:22 \
  -v gitea-data:/data \
  -e USER_UID=1000 \
  -e USER_GID=1000 \
  luckyrobots/gitea-parquet-viewer:latest
```

### Option 2: Using Docker Compose

1. Download the `docker-compose.yml` file from this repository
2. Run the following command:

```bash
docker-compose up -d
```

## Accessing Gitea

After starting the container, you can access Gitea at:

```
http://localhost:3000/
```

## Using the Parquet Viewer

1. Create a repository in Gitea
2. Upload a Parquet file to the repository
3. Click on the Parquet file in the repository file list
4. The Parquet viewer will automatically display the file contents

## Building the Docker Image

If you want to build the Docker image yourself:

```bash
# Make the build script executable
chmod +x build-and-push.sh

# Build and push the image
DOCKER_USERNAME=yourusername DOCKER_PASSWORD=yourpassword ./build-and-push.sh
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
