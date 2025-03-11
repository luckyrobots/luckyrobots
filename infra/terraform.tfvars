# Copy this file to terraform.tfvars and update the values
hcloud_token         = "hetzner_cloud_api_token"
server_type          = "cpx31"
location             = "nbg1"
gitea_admin_username = "giteaadmin"
gitea_admin_password = "StrongPassword123!"
gitea_admin_email    = "admin@luckyrobots.ai"
ssh_public_key_path  = "~/.ssh/id_ed25519.pub"
# ssh_private_key_path = "~/.ssh/id_ed25519" # Uncomment and modify if needed

# Server configuration
# datacenter  = "nbg1-dc3" # Uncomment and specify if needed

# Storage configuration
additional_storage_needed = true # Set to true to create additional volumes

# SSH key path
# ssh_private_key_path = "~/.ssh/id_ed25519" # Uncomment and modify if needed 