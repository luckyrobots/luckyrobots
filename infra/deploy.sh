#!/bin/bash
set -e

# Default values
ACTION="apply"
AUTO_APPROVE=""
VAR_FILE="terraform.tfvars"
ENV_FILE=""
USE_ENV=false
VERBOSE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --destroy)
      ACTION="destroy"
      shift
      ;;
    --plan)
      ACTION="plan"
      shift
      ;;
    --auto-approve)
      AUTO_APPROVE="-auto-approve"
      shift
      ;;
    --var-file)
      VAR_FILE="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      USE_ENV=true
      shift 2
      ;;
    --debug)
      VERBOSE="TF_LOG=DEBUG"
      echo "Debug mode enabled"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
  echo "Initializing Terraform..."
  terraform init
fi

# Handle environment variables if specified
if [ "$USE_ENV" = true ]; then
  if [ -z "$ENV_FILE" ]; then
    # Default to .env if no file specified
    ENV_FILE=".env"
  fi
  
  if [ ! -f "$ENV_FILE" ]; then
    if [ -f ".env.example" ] && [ "$ENV_FILE" = ".env" ]; then
      echo ".env file not found. Creating from example..."
      cp .env.example .env
      echo "Please edit .env with your actual values, then run this script again."
      exit 0
    else
      echo "Error: Environment file $ENV_FILE not found!"
      exit 1
    fi
  fi
  
  echo "Converting environment variables from $ENV_FILE to Terraform variables..."
  chmod +x scripts/env-to-tfvars.sh
  ./scripts/env-to-tfvars.sh "$ENV_FILE"
  
  # Check if the .tfvars file was successfully generated
  if [ ! -f "generated.tfvars" ]; then
    echo "Error: Failed to generate tfvars file from environment variables!"
    exit 1
  fi
  
  echo "Generated variables file content (with sensitive data masked):"
  grep -v "password\|token" generated.tfvars || echo "No variables to display"
  
  VAR_FILE="generated.tfvars"
  echo "Using generated variables from $ENV_FILE"
else
  # Check if var file exists
  if [ ! -f "$VAR_FILE" ] && [ "$VAR_FILE" != "terraform.tfvars" ]; then
    echo "Error: Variable file $VAR_FILE not found!"
    exit 1
  fi

  # If default var file doesn't exist and no custom one specified, create from example
  if [ ! -f "terraform.tfvars" ] && [ "$VAR_FILE" == "terraform.tfvars" ]; then
    echo "terraform.tfvars not found. Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "Please edit terraform.tfvars with your actual values, then run this script again."
    exit 0
  fi
fi

# Run the appropriate Terraform command
case $ACTION in
  "apply")
    echo "Applying Terraform configuration..."
    if [ -n "$VERBOSE" ]; then
      # In debug mode, show the command first
      echo "Running: env $VERBOSE terraform apply $AUTO_APPROVE -var-file=\"$VAR_FILE\""
      # Use env command to set the environment variable
      env $VERBOSE terraform apply $AUTO_APPROVE -var-file="$VAR_FILE"
    else
      terraform apply $AUTO_APPROVE -var-file="$VAR_FILE"
    fi
    
    # Display useful information after successful apply
    if [ $? -eq 0 ]; then
      echo "---------------------------------------"
      echo "Deployment completed successfully!"
      echo "---------------------------------------"
      echo "Access information:"
      terraform output
    else
      echo "---------------------------------------"
      echo "Deployment failed!"
      echo "---------------------------------------"
      echo "For more details, run with --debug flag"
      echo "If SSH connection failed, check that:"
      echo "1. Your SSH key is correctly specified"
      echo "2. Your server has a public IP and is reachable"
      echo "3. The firewall allows SSH connections"
    fi
    ;;
  "plan")
    echo "Planning Terraform configuration..."
    if [ -n "$VERBOSE" ]; then
      env $VERBOSE terraform plan -var-file="$VAR_FILE"
    else
      terraform plan -var-file="$VAR_FILE"
    fi
    ;;
  "destroy")
    echo "Destroying Terraform infrastructure..."
    if [ -n "$VERBOSE" ]; then
      env $VERBOSE terraform destroy $AUTO_APPROVE -var-file="$VAR_FILE"
    else
      terraform destroy $AUTO_APPROVE -var-file="$VAR_FILE"
    fi
    ;;
esac 