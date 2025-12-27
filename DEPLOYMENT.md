# PrimeData Deployment Guide

This guide covers deploying PrimeData to GCP using Terraform and GitHub Actions.

## Architecture

- **Cloud SQL (PostgreSQL)**: Database (already created)
- **Compute Engine VM**: Runs all containers (Airflow, Qdrant, Backend, Frontend)
- **Cloud Storage (GCS)**: Object storage (replaces MinIO)
- **Terraform**: Infrastructure as Code
- **GitHub Actions**: CI/CD pipelines

## Prerequisites

1. GCP account with billing enabled
2. GitHub repository with Actions enabled
3. Terraform >= 1.0 installed locally (for manual deployment)
4. GCP Cloud SDK installed

## Quick Start

### 1. Initial Setup

```bash
# Clone repository
git clone https://github.com/neelam53yadav/aird.git
cd aird
git checkout db-fixes

# Authenticate with GCP
gcloud auth login
gcloud config set project project-f3c8a334-a3f2-4f66-a06
```

### 2. Deploy Infrastructure (Terraform)

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply (creates VM, firewall rules, service accounts)
terraform apply
```

**Outputs:**
- VM External IP
- Service Account Email
- Database Connection Name

### 3. Configure GitHub Secrets

Go to GitHub → Settings → Secrets and variables → Actions

Add these secrets:

1. **GCP_SA_KEY**: Service account JSON key
   ```bash
   gcloud iam service-accounts keys create github-actions-key.json \
     --iam-account=github-actions@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com
   # Copy contents of github-actions-key.json
   ```

2. **VM_USERNAME**: Your GCP username (from Cloud Shell)

3. **VM_SSH_KEY**: Private SSH key for VM access
   ```bash
   ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions
   # Add public key to VM
   gcloud compute instances add-metadata primedata-beta \
     --zone=us-central1-c \
     --metadata-from-file ssh-keys=~/.ssh/github_actions.pub
   # Copy private key to GitHub secret
   ```

### 4. Setup GCS Service Account

```bash
# Create service account for GCS access
gcloud iam service-accounts create primedata-storage \
  --display-name="PrimeData Storage Service Account"

# Grant storage permissions
gsutil iam ch serviceAccount:primedata-storage@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com:roles/storage.admin gs://primedata-raw
gsutil iam ch serviceAccount:primedata-storage@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com:roles/storage.admin gs://primedata-processed
gsutil iam ch serviceAccount:primedata-storage@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com:roles/storage.admin gs://primedata-exports

# Create and download key
gcloud iam service-accounts keys create primedata-storage-key.json \
  --iam-account=primedata-storage@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com
```

### 5. Configure Environment Variables

On the VM, create `.env.production`:

```bash
# SSH to VM
gcloud compute ssh primedata-beta --zone=us-central1-c

# Create environment file
cat > /opt/primedata/.env.production << EOF
DATABASE_URL=postgresql://primedata:123Hello!@34.171.200.114:5432/primedata
AIRFLOW_DB_URL=postgresql://primedata:123Hello!@34.171.200.114:5432/airflow
MINIO_HOST=storage.googleapis.com
MINIO_ACCESS_KEY=<GCS_SERVICE_ACCOUNT_KEY>
MINIO_SECRET_KEY=<GCS_SERVICE_ACCOUNT_SECRET>
MINIO_SECURE=true
GOOGLE_APPLICATION_CREDENTIALS=/opt/primedata/keys/primedata-storage-key.json
QDRANT_HOST=qdrant
QDRANT_PORT=6333
FRONTEND_URL=http://<VM_IP>:3000
NEXT_PUBLIC_API_URL=http://<VM_IP>:8000
NEXTAUTH_URL=http://<VM_IP>:3000
CORS_ORIGINS=["http://<VM_IP>:3000"]
JWT_SECRET_KEY=<GENERATE_64_CHAR_SECRET>
NEXTAUTH_SECRET=<GENERATE_64_CHAR_SECRET>
DISABLE_AUTH=false
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=<GENERATE_PASSWORD>
EOF
```

### 6. Deploy Application

**Option A: Via GitHub Actions (Recommended)**

1. Push code to `db-fixes` branch
2. GitHub Actions will automatically deploy
3. Monitor in Actions tab

**Option B: Manual Deployment**

```bash
# Use deployment script
./infra/scripts/deploy.sh

# Or manually
gcloud compute ssh primedata-beta --zone=us-central1-c
cd /opt/primedata
docker-compose -f infra/docker-compose.prod.yml up -d --build
```

## Accessing Services

After deployment, services will be available at:

- **Frontend**: http://VM_IP:3000
- **Backend API**: http://VM_IP:8000
- **API Docs**: http://VM_IP:8000/docs
- **Airflow**: http://VM_IP:8080
- **Qdrant Dashboard**: http://VM_IP:6333/dashboard

## Database Migrations

Migrations run automatically on deployment. To run manually:

```bash
docker-compose -f infra/docker-compose.prod.yml exec backend alembic upgrade head
```

## Monitoring

### Check Service Status

```bash
# SSH to VM
gcloud compute ssh primedata-beta --zone=us-central1-c

# Check containers
docker ps

# Check logs
docker-compose -f infra/docker-compose.prod.yml logs -f
```

### Health Checks

```bash
# Backend
curl http://VM_IP:8000/health

# Airflow
curl http://VM_IP:8080/health
```

## Troubleshooting

### VM Not Accessible

```bash
# Check VM status
gcloud compute instances describe primedata-beta --zone=us-central1-c

# Check firewall rules
gcloud compute firewall-rules list --filter="name~primedata"
```

### Containers Not Starting

```bash
# Check logs
docker-compose -f infra/docker-compose.prod.yml logs

# Check environment variables
docker-compose -f infra/docker-compose.prod.yml config
```

### Database Connection Issues

```bash
# Test connection
psql -h 34.171.200.114 -U primedata -d primedata

# Check Cloud SQL instance
gcloud sql instances describe primedata-postgres
```

### GCS Access Issues

```bash
# Verify service account permissions
gsutil iam get gs://primedata-raw

# Test access
gsutil ls gs://primedata-raw
```

## Updating Application

### Via GitHub Actions

1. Make changes
2. Commit and push to `db-fixes` branch
3. GitHub Actions will automatically deploy

### Manual Update

```bash
# SSH to VM
gcloud compute ssh primedata-beta --zone=us-central1-c

# Pull latest code
cd /opt/primedata
git pull origin db-fixes

# Rebuild and restart
docker-compose -f infra/docker-compose.prod.yml up -d --build
```

## Scaling

### Increase VM Size

```bash
# Stop VM
gcloud compute instances stop primedata-beta --zone=us-central1-c

# Change machine type
gcloud compute instances set-machine-type primedata-beta \
  --zone=us-central1-c \
  --machine-type=e2-standard-4

# Start VM
gcloud compute instances start primedata-beta --zone=us-central1-c
```

## Cleanup

To destroy all infrastructure:

```bash
cd infra/terraform
terraform destroy
```

**Warning**: This will delete everything!

## Multi-Cloud Portability

This setup can be adapted for:

- **AWS**: Replace Compute Engine with EC2, GCS with S3
- **Azure**: Replace with Azure VMs and Blob Storage
- **On-Premises**: Use local VMs and object storage

Key changes:
- Provider configuration in Terraform
- Resource types (EC2 vs Compute Engine)
- Storage endpoints (S3 vs GCS)

## Security Best Practices

1. **Use Secret Manager** for sensitive values (not `.env` files)
2. **Enable SSL/TLS** for all connections
3. **Restrict firewall rules** to specific IPs
4. **Use IAM roles** instead of service account keys when possible
5. **Rotate secrets** regularly
6. **Enable audit logging** for GCP resources

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Check GitHub Actions: Actions tab
3. Check GCP Console: Compute Engine, Cloud SQL
4. Review Terraform state: `terraform show`

