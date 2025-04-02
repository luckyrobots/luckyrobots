output "gitea_ip" {
  description = "Public IP address of the Gitea server"
  value       = hcloud_server.gitea.ipv4_address
}

output "gitea_admin_username" {
  description = "Gitea admin username"
  value       = var.gitea_admin_username
}

output "gitea_admin_password" {
  description = "Gitea admin password"
  value       = var.gitea_admin_password
  sensitive   = true
}

output "ssh_command" {
  description = "Command to SSH into the server"
  value       = "ssh-keygen -R ${hcloud_server.gitea.ipv4_address} && ssh -i ${var.ssh_private_key_path} root@${hcloud_server.gitea.ipv4_address}"
}

output "gitea_url" {
  description = "URL to access Gitea"
  value       = "http://${hcloud_server.gitea.ipv4_address}:3000/"
} 