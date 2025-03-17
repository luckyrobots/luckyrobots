# Gitea Server Infrastructure

This directory contains Terraform configurations to deploy a Gitea server on Hetzner Cloud. The configuration is organized in a modular way to improve maintainability.

## File Structure

- `main.tf`: Main Terraform configuration containing provider settings and resources
- `variables.tf`: Variable definitions
- `outputs.tf`: Output definitions
- `terraform.tfvars.example`: Example variable values (copy to `terraform.tfvars` and customize)
- `.env.example`: Example environment variables (copy to `.env` and customize)
- `deploy.sh`: Deployment script to simplify Terraform operations
- `scripts/setup-gitea.sh`: Shell script for Gitea setup and configuration
- `scripts/env-to-tfvars.sh`: Helper script to convert environment variables to Terraform variables

## Prerequisites

1. Hetzner Cloud account with an API token
2. Terraform installed on your local machine
3. SSH key pair for server access

## Getting Started

### Using terraform.tfvars (Standard method)

1. Copy the example variables file:
   ```
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your actual values.

3. Make the deployment script executable (if not already):
   ```
   chmod +x deploy.sh
   ```

4. Run the deployment script:
   ```
   ./deploy.sh
   ```

### Using Environment Variables (.env file)

1. Copy the example environment file:
   ```
   cp .env.example .env
   ```

2. Edit `.env` with your actual values.

3. Make the deployment script executable (if not already):
   ```
   chmod +x deploy.sh
   ```

4. Run the deployment script with the --env-file flag:
   ```
   ./deploy.sh --env-file .env
   ```

## Deployment Options

The `deploy.sh` script provides several options for flexibility:

- `--plan`: Plan the changes without applying
   ```
   ./deploy.sh --plan
   ```

- `--destroy`: Destroy the infrastructure
   ```
   ./deploy.sh --destroy
   ```

- `--auto-approve`: Skip the confirmation prompt
   ```
   ./deploy.sh --auto-approve
   ```

- `--var-file`: Use a custom variable file
   ```
   ./deploy.sh --var-file=production.tfvars
   ```

- `--env-file`: Use environment variables from a .env file
   ```
   ./deploy.sh --env-file=production.env
   ```

## Example deploy plan command from .env file

```
./deploy.sh --plan --env-file .env
```

## Multiple Environments

You can maintain separate environment files for different deployments:

```
# Development environment
./deploy.sh --env-file dev.env

# Production environment
./deploy.sh --env-file prod.env
```

## Access

After successful deployment, you can access Gitea using:

1. Web UI: http://SERVER_IP:3000
2. SSH for Git operations: ssh://git@SERVER_IP:2222
3. ssh -i ~/.ssh/id_ed25519 root@167.235.246.115

The admin credentials used for setup are specified in the configuration file. 