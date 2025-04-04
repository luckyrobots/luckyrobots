terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = ">= 1.0.0"
    }
  }
}

provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_ssh_key" "default" {
  name       = "luckyrobots-key"
  public_key = file(var.ssh_public_key_path)
}

resource "hcloud_volume" "gitea_storage" {
  name       = "gitea-storage"
  size       = 3000  # 3 TB in GB
  location   = var.location
  format     = "ext4"
  automount  = false
  
  labels = {
    type = "gitea"
    purpose = "storage"
  }
  
  #  lifecycle {
  #   prevent_destroy = true
  # }
}

resource "hcloud_server" "gitea" {
  name        = "gt-server"
  server_type = var.server_type
  image       = "ubuntu-22.04"
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.default.name]
  
  # Add datacenter selection to help with placement issues
  datacenter  = var.datacenter
  
  # Add retries for server creation
  timeouts {
    create = "10m"
  }

  connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    host        = self.ipv4_address
    timeout     = "10m"
  }

  # Wait for cloud-init to complete
  provisioner "remote-exec" {
    connection {
      type        = "ssh"
      host        = self.ipv4_address
      user        = "root"
      private_key = file(var.ssh_private_key_path)
      timeout     = "5m"
    }
    inline = [
      "cloud-init status --wait || echo 'Cloud-init failed or not available, continuing anyway'",
      "apt-get update",
      "apt-get install -y curl jq",
      "echo 'Server is ready for software installation'"
    ]
  }

  # Upload the setup script
  provisioner "file" {
    connection {
      type        = "ssh"
      host        = self.ipv4_address
      user        = "root"
      private_key = file(var.ssh_private_key_path)
      timeout     = "5m"
    }
    source      = "${path.module}/scripts/setup-gitea.sh"
    destination = "/root/setup-gitea.sh"
  }

  # Make sure the server is created before attaching the volume
  depends_on = [hcloud_volume.gitea_storage]
}


# Attach the volumes to the server
resource "hcloud_volume_attachment" "gitea_storage_attachment" {
  volume_id = hcloud_volume.gitea_storage.id
  server_id = hcloud_server.gitea.id
  automount = true
}

# Ensure the volume is mounted before we run the setup script
# This improves the dependency order
resource "null_resource" "volume_mount_delay" {
  depends_on = [hcloud_volume_attachment.gitea_storage_attachment]

  connection {
    type        = "ssh"
    host        = hcloud_server.gitea.ipv4_address
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    timeout     = "5m"
  }

  provisioner "remote-exec" {
    inline = [
      "echo 'Waiting for volume to be mounted...'",      # Wait for the device to appear
      "timeout 60 bash -c 'until ls /dev/disk/by-id/scsi-0HC_Volume_* &>/d...\"; sleep 5; done'",
      "mkdir -p /mnt/gitea-storage",
      "if ! mountpoint -q /mnt/gitea-storage; then VOLUME_DEVICE=$(ls -la /dev/disk/by-id/scsi-0HC_Volume_* | grep -o '/dev/sd[a-z]') && mount $VOLUME_DEVICE /mnt/gitea-storage; fi",
      "echo 'Volume mounted successfully'",
      "mkdir -p /mnt/gitea-storage/postgres /mnt/gitea-storage/gitea /mnt/gitea-storage/runner",
      "mkdir -p /mnt/gitea-extras/repositories",
      "chown -R 1000:1000 /mnt/gitea-storage || echo 'Failed to set ownership, will try again in setup script'",
      "chown -R 1000:1000 /mnt/gitea-extras || echo 'Failed to set ownership, will try again in setup script'",
      "touch /mnt/gitea-storage/test_file && echo 'Volume is writeable' || echo 'WARNING: Volume is not writeable!'",
      "echo 'Current mounts:' && mount | grep -i gitea || echo 'No gitea mounts found'",
      "systemctl status docker || echo 'Docker service not running properly'"
    ]
  }
}

resource "null_resource" "run_gitea_setup" {
  depends_on = [null_resource.volume_mount_delay, hcloud_server.gitea]

  connection {
    type        = "ssh"
    host        = hcloud_server.gitea.ipv4_address
    user        = "root"
    private_key = file(var.ssh_private_key_path)
    timeout     = "15m"
  }

  # Create the wrapper script using a series of echo statements
  provisioner "remote-exec" {
    inline = [
      "echo '#!/bin/bash' > /root/run-setup-background.sh",
      "echo '# This is a wrapper script that runs the setup in background' >> /root/run-setup-background.sh",
      "echo '# and makes sure terraform does not hang' >> /root/run-setup-background.sh",
      "echo '' >> /root/run-setup-background.sh",
      "echo '# Ensure the log directory exists' >> /root/run-setup-background.sh",
      "echo 'mkdir -p /root/logs' >> /root/run-setup-background.sh",
      "echo '' >> /root/run-setup-background.sh",
      "echo '# Clear any previous logs' >> /root/run-setup-background.sh",
      "echo 'rm -f /root/logs/setup-gitea.log' >> /root/run-setup-background.sh",
      "echo '' >> /root/run-setup-background.sh",
      "echo '# Start the setup script in background with timeout and write to log file' >> /root/run-setup-background.sh",
      "echo 'echo \"Starting setup script in background at $(date)\" > /root/logs/setup-gitea.log' >> /root/run-setup-background.sh",
      "echo 'nohup timeout 1800 bash -x /root/setup-gitea.sh \"${var.gitea_admin_username}\" \"${var.gitea_admin_password}\" \"${var.gitea_admin_email}\" >> /root/logs/setup-gitea.log 2>&1 &' >> /root/run-setup-background.sh",
      "echo '' >> /root/run-setup-background.sh",
      "echo '# Wait a bit to ensure script starts' >> /root/run-setup-background.sh",
      "echo 'sleep 5' >> /root/run-setup-background.sh",
      "echo '' >> /root/run-setup-background.sh",
      "echo '# Show that we started the process' >> /root/run-setup-background.sh",
      "echo 'echo \"Setup script started in background with PID: $!\" >> /root/logs/setup-gitea.log' >> /root/run-setup-background.sh",
      "echo 'echo \"You can check progress with cat /root/logs/setup-gitea.log\"' >> /root/run-setup-background.sh",
      "echo 'echo \"Background setup started.\"' >> /root/run-setup-background.sh",
      "chmod +x /root/run-setup-background.sh",
      "ls -la /root/run-setup-background.sh"
    ]
  }

  # Run the wrapper script
  provisioner "remote-exec" {
    inline = [
      "echo 'Running setup script in background...'",
      "export HETZNER_OBJECT_STORAGE_ACCESS_KEY='${var.hetzner_object_storage_access_key}'",
      "export HETZNER_OBJECT_STORAGE_SECRET_KEY='${var.hetzner_object_storage_secret_key}'",
      "export HETZNER_OBJECT_STORAGE_BUCKET_NAME='${var.hetzner_object_storage_bucket_name}'",
      "export HETZNER_S3_ENDPOINT='nbg1.your-objectstorage.com'",
      "bash /root/run-setup-background.sh"
    ]
  }

  # Create a marker file to indicate we've reached this point
  provisioner "remote-exec" {
    inline = [
      "echo 'Setup process initiated in the background.' > /root/setup-initiated.txt",
      "echo 'Terraform deployment will continue, the actual setup is running in background.'",
      "echo 'You can SSH to the server and check progress with: cat /root/logs/setup-gitea.log'"
    ]
  }
}
