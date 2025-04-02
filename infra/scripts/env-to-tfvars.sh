#!/bin/bash
set -e

# Default .env file location
ENV_FILE="${1:-.env}"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: Environment file '$ENV_FILE' not found!"
  exit 1
fi

# Output file
TFVARS_FILE="generated.tfvars"

echo "# This file is auto-generated from $ENV_FILE - do not edit directly" > "$TFVARS_FILE"
echo "# Generated on $(date)" >> "$TFVARS_FILE"
echo "" >> "$TFVARS_FILE"

# Read each line of the .env file
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip empty lines and comments
  if [[ -z "$line" || "$line" == \#* ]]; then
    continue
  fi
  
  # Extract key and value
  if [[ "$line" =~ ^([A-Za-z0-9_]+)=(.*)$ ]]; then
    key="${BASH_REMATCH[1]}"
    value="${BASH_REMATCH[2]}"
    
    # Remove any surrounding quotes from the value
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    
    # Remove any carriage returns, newlines or trailing spaces
    value=$(echo "$value" | tr -d '\r\n')
    value="${value%"${value##*[![:space:]]}"}" # Remove trailing whitespace
    
    # Convert environment variable naming to terraform variable naming (lowercase)
    tf_key=$(echo "$key" | tr '[:upper:]' '[:lower:]')
    
    # Write to tfvars file with proper HCL syntax
    printf "%s = \"%s\"\n" "$tf_key" "$value" >> "$TFVARS_FILE"
  fi
done < "$ENV_FILE"

echo "Successfully generated $TFVARS_FILE from $ENV_FILE"
echo "Found $(grep -c "=" "$TFVARS_FILE") variables" 