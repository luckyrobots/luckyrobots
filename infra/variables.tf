variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  sensitive   = true
}

variable "server_type" {
  description = "Server type/size to use"
  default     = "cpx41"
}

variable "location" {
  description = "Datacenter location"
  default     = "fsn1"
}

variable "gitea_admin_username" {
  description = "Gitea admin username"
  default     = "giteaadmin"
}

variable "gitea_admin_password" {
  description = "Gitea admin password"
  default     = "StrongPassword123!"
  sensitive   = true
}

variable "gitea_admin_email" {
  description = "Gitea admin email"
  default     = "admin@example.com"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  default     = "~/.ssh/id_ed25519.pub"
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key"
  default     = "~/.ssh/id_ed25519"
}

variable "datacenter" {
  description = "The datacenter to deploy to (more specific than location)"
  type        = string
  default     = null
}

variable "gitea_runner_registration_token" {
  description = "Gitea runner registration token"
  type        = string
  sensitive   = true
}

variable "hetzner_object_storage_access_key" {
  description = "Hetzner Object Storage access key"
  type        = string
  sensitive   = true
}

variable "hetzner_object_storage_secret_key" {
  description = "Hetzner Object Storage secret key"
  type        = string
  sensitive   = true
}

variable "hetzner_object_storage_bucket_name" {
  description = "Hetzner Object Storage bucket name"
  type        = string
  default     = "gitea-lfs"
}
