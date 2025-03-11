# Troubleshooting Gitea Deployment

This guide helps you diagnose and fix common issues with the Gitea deployment.

## Common Errors and Solutions

### Error: remote-exec provisioner error

If you see an error like:
```
hcloud_server.gitea (remote-exec): (output suppressed due to sensitive value in config)
Error: remote-exec provisioner error
```

This means the script execution on the remote server failed. Here's how to debug it:

1. **Enable debug mode**:
   ```bash
   ./deploy.sh --debug
   ```
   This will show more detailed logs.

2. **SSH into the server manually**:
   After the server is created but the script fails, you can SSH in:
   ```bash
   ssh -i ~/.ssh/id_ed25519 root@SERVER_IP
   ```
   
3. **Check the script logs**:
   Once connected, run:
   ```bash
   cat /var/log/cloud-init-output.log
   docker logs robotea
   ```

### SSH Connection Issues

If Terraform can't connect to the server via SSH:

1. **Check your SSH key location**:
   Ensure the paths in `terraform.tfvars` or `.env` file match your actual SSH key paths.

2. **Verify server IP**:
   ```bash
   terraform output gitea_ip
   ```
   Then try to ping and SSH to this IP manually.

3. **Check firewall rules**:
   Ensure port 22 is open on the server.

### Gitea Installation Failures

If Gitea installation fails:

1. **Check if Docker is running**:
   ```bash
   systemctl status docker
   ```

2. **Check if Gitea container is running**:
   ```bash
   docker ps | grep robotea
   ```

3. **View Gitea logs**:
   ```bash
   docker logs robotea
   ```

4. **Check port availability**:
   ```bash
   netstat -tulpn | grep 3000
   ```

### Variables Not Available

If variables are not being passed correctly:

1. **Verify your `.env` or `terraform.tfvars` file**:
   Ensure all required variables are properly defined.

2. **Test variable generation**:
   ```bash
   ./scripts/env-to-tfvars.sh .env
   cat generated.tfvars
   ```

3. **Check for syntax errors**:
   Look for malformed quotes or special characters in your configuration files.

## Quick Recovery Steps

1. **Destroy and recreate**:
   ```bash
   ./deploy.sh --destroy --auto-approve
   ./deploy.sh
   ```

2. **Manually fix and reapply**:
   If the server is created but Gitea installation failed:
   - SSH into the server
   - Run the setup script manually: 
     ```bash
     /tmp/setup-gitea.sh admin StrongPassword123 admin@example.com
     ```

3. **Increase timeouts**:
   Timeouts are already set in the Terraform configuration, but you can increase them in `main.tf` if needed.


## To fix SSH access `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!`:
```
ssh-keygen -R 167.235.246.115
```

## Getting Help

If you can't resolve the issue using this guide:

1. Check the Terraform logs with `--debug` flag
2. SSH into the server and check logs
3. Update the scripts with more detailed error messages 