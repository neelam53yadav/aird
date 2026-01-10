# GitHub Actions Workflows

This directory contains CI/CD workflows for PrimeData.

## Workflows

### 1. `ci.yml` - Continuous Integration

Runs on every push and pull request:
- Lints backend code (flake8, black, isort)
- Runs backend tests
- Lints frontend code
- Type checks frontend
- Builds Docker images

### 2. `deploy-infra.yml` - Infrastructure Deployment

Deploys Terraform infrastructure:
- Runs on changes to `infra/terraform/**`
- Can be triggered manually
- Validates and applies Terraform configuration

**Secrets Required:**
- None! Uses Workload Identity Federation (no service account keys needed)
- `VM_USERNAME`: SSH username for VM (for deploy-app workflow)
- `VM_SSH_KEY`: Private SSH key for VM access (for deploy-app workflow)

### 3. `deploy-app.yml` - Application Deployment

Deploys application to VM:
- Runs on changes to `backend/**`, `ui/**`, or `infra/docker-compose.prod.yml`
- Copies files to VM
- Builds and starts Docker containers
- Runs database migrations

**Secrets Required:**
- None for GCP authentication! Uses Workload Identity Federation
- `VM_USERNAME`: SSH username for VM
- `VM_SSH_KEY`: Private SSH key for VM access

## Setup

### 1. Setup Workload Identity Federation (Already Done!)

Workload Identity Federation is already configured. This is more secure than service account keys.

**Workload Identity Provider:**
```
projects/890841479962/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

**Service Account:**
```
github-actions@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com
```

### 2. Add GitHub Secrets

Go to GitHub repository → Settings → Secrets and variables → Actions

**Required Secrets:**
- `VM_USERNAME`: Your VM username (usually your GCP username, e.g., `neelamvivaan23`)
- `VM_SSH_KEY`: Your private SSH key for VM access

**Note:** You do NOT need `GCP_SA_KEY` anymore! Workload Identity Federation handles authentication automatically.

### 3. Generate SSH Key for VM

```bash
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions
```

Add public key to VM:
```bash
gcloud compute instances add-metadata primedata-beta \
  --zone=us-central1-c \
  --metadata-from-file ssh-keys=~/.ssh/github_actions.pub
```

Add private key to GitHub secrets as `VM_SSH_KEY`.

## Usage

### Manual Deployment

1. Go to Actions tab in GitHub
2. Select workflow
3. Click "Run workflow"
4. Choose branch and options
5. Click "Run workflow"

### Automatic Deployment

Workflows run automatically on:
- Push to `main` or `db-fixes` branches
- Changes to relevant files
- Pull requests (CI only)

## Troubleshooting

### Terraform Apply Fails

- Check GCP permissions
- Verify service account has required roles
- Check Terraform state

### Deployment Fails

- Verify VM is running
- Check SSH key is correct
- Verify environment variables are set
- Check Docker is installed on VM

### Health Checks Fail

- Wait longer for services to start
- Check container logs
- Verify ports are open in firewall

