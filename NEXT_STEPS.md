# Next Steps - Deployment Guide

## ✅ Completed

- [x] Workload Identity Federation configured
- [x] Service account permissions granted
- [x] GitHub secrets added (VM_USERNAME, VM_SSH_KEY)
- [x] Terraform configuration ready
- [x] GitHub Actions workflows ready
- [x] Idempotency checks in place

## 🚀 Next Steps

### Step 1: Commit and Push Code

First, commit all the infrastructure changes to your repository:

```bash
# On your local machine
cd /Users/atul7717/Desktop/Code/aird

# Check what files have changed
git status

# Add all new files
git add .

# Commit
git commit -m "Add Terraform infrastructure and GitHub Actions workflows with Workload Identity Federation"

# Push to db-fixes branch
git push origin db-fixes
```

### Step 2: Deploy Infrastructure (Terraform)

After pushing, GitHub Actions will automatically trigger the `deploy-infra.yml` workflow.

**Option A: Automatic (Recommended)**
- Workflow triggers automatically on push to `db-fixes`
- Monitor at: https://github.com/neelam53yadav/aird/actions

**Option B: Manual Trigger**
1. Go to: https://github.com/neelam53yadav/aird/actions
2. Select "Deploy Infrastructure" workflow
3. Click "Run workflow"
4. Choose branch: `db-fixes`
5. Choose action: `apply`
6. Click "Run workflow"

**What it does:**
- Creates VM instance (`primedata-beta`)
- Creates firewall rules
- Creates service account
- Grants permissions

**Expected time:** 3-5 minutes

### Step 3: Get VM IP Address

After infrastructure deployment completes:

**Option A: From Terraform Output**
- Check GitHub Actions logs for Terraform output
- Look for `vm_external_ip` value

**Option B: From GCP Console**
```bash
# In Cloud Shell
gcloud compute instances describe primedata-beta \
  --zone=us-central1-c \
  --format="value(networkInterfaces[0].accessConfig[0].natIP)"
```

**Option C: From GCP Console UI**
- Go to: Compute Engine → VM instances
- Find `primedata-beta`
- Copy External IP

### Step 4: Add SSH Key to VM

Once VM is created, add your SSH public key:

```bash
# In Cloud Shell
# If you haven't generated the key yet:
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions -N ""

# Add public key to VM
gcloud compute instances add-metadata primedata-beta \
  --zone=us-central1-c \
  --metadata-from-file ssh-keys=~/.ssh/github_actions.pub
```

**Note:** If you already added the key when creating the secret, you can skip this step if the key matches.

### Step 5: Create Environment File on VM

SSH to the VM and create the environment configuration:

```bash
# SSH to VM (replace VM_IP with actual IP)
gcloud compute ssh primedata-beta --zone=us-central1-c

# Once connected to VM, create environment file
sudo mkdir -p /opt/primedata
sudo chown $USER:$USER /opt/primedata
cd /opt/primedata

# Create .env.production file
cat > .env.production << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://primedata:123Hello!@34.171.200.114:5432/primedata
AIRFLOW_DB_URL=postgresql://primedata:123Hello!@34.171.200.114:5432/airflow

# Cloud Storage (GCS) Configuration
# For GCS, use S3 compatibility mode
MINIO_HOST=storage.googleapis.com
MINIO_ACCESS_KEY=<YOUR_GCS_SERVICE_ACCOUNT_KEY>
MINIO_SECRET_KEY=<YOUR_GCS_SERVICE_ACCOUNT_SECRET>
MINIO_SECURE=true

# Service Account Key Path (if using key file)
GOOGLE_APPLICATION_CREDENTIALS=/opt/primedata/keys/primedata-storage-key.json

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

# Application Configuration
FRONTEND_URL=http://<VM_IP>:3000
NEXT_PUBLIC_API_URL=http://<VM_IP>:8000
NEXTAUTH_URL=http://<VM_IP>:3000
CORS_ORIGINS=["http://<VM_IP>:3000"]

# Security
JWT_SECRET_KEY=<GENERATE_64_CHAR_SECRET>
NEXTAUTH_SECRET=<GENERATE_64_CHAR_SECRET>
DISABLE_AUTH=false

# Airflow Configuration
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=<GENERATE_PASSWORD>
AIRFLOW_SECRET_KEY=<GENERATE_SECRET>
EOF

# Replace <VM_IP> with actual VM IP
# Replace <YOUR_GCS_SERVICE_ACCOUNT_KEY> and <YOUR_GCS_SERVICE_ACCOUNT_SECRET>
# Generate secrets (see below)

# Exit VM
exit
```

**Generate Secrets:**
```bash
# Generate JWT secret (64 chars)
openssl rand -hex 32

# Generate NextAuth secret (64 chars)
openssl rand -hex 32

# Generate Airflow password
openssl rand -base64 16

# Generate Airflow secret key
openssl rand -hex 32
```

### Step 6: Setup GCS Service Account Key (if needed)

If you need to use GCS with service account key:

```bash
# In Cloud Shell, create key for primedata-storage service account
gcloud iam service-accounts keys create primedata-storage-key.json \
  --iam-account=primedata-storage@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com

# Copy key to VM
gcloud compute scp primedata-storage-key.json \
  primedata-beta:/opt/primedata/keys/ \
  --zone=us-central1-c

# Or use Workload Identity (no key needed) - recommended
```

**Note:** If using Workload Identity, you don't need service account keys. The VM's service account will automatically authenticate.

### Step 7: Deploy Application

After infrastructure is deployed and environment is configured:

**Option A: Automatic (Recommended)**
- Push any change to `backend/`, `ui/`, or `infra/docker-compose.prod.yml`
- GitHub Actions will automatically deploy

**Option B: Manual Trigger**
1. Go to: https://github.com/neelam53yadav/aird/actions
2. Select "Deploy Application" workflow
3. Click "Run workflow"
4. Choose branch: `db-fixes`
5. Click "Run workflow"

**What it does:**
- Copies code to VM
- Builds Docker images
- Starts containers
- Runs database migrations

**Expected time:** 5-10 minutes

### Step 8: Verify Deployment

After deployment completes, verify services:

```bash
# Check containers are running
gcloud compute ssh primedata-beta --zone=us-central1-c
docker ps

# Check service health
curl http://localhost:8000/health  # Backend
curl http://localhost:8080/health  # Airflow
curl http://localhost:6333/health  # Qdrant

# Exit VM
exit
```

**Access Services:**
- Frontend: http://VM_IP:3000
- Backend API: http://VM_IP:8000
- API Docs: http://VM_IP:8000/docs
- Airflow: http://VM_IP:8080
- Qdrant Dashboard: http://VM_IP:6333/dashboard

## Quick Start Commands

### All-in-One Setup Script

```bash
# 1. Push code (on local machine)
cd /Users/atul7717/Desktop/Code/aird
git add .
git commit -m "Deploy infrastructure and application"
git push origin db-fixes

# 2. Wait for infrastructure deployment (3-5 min)
# Monitor: https://github.com/neelam53yadav/aird/actions

# 3. Get VM IP (in Cloud Shell)
VM_IP=$(gcloud compute instances describe primedata-beta \
  --zone=us-central1-c \
  --format="value(networkInterfaces[0].accessConfig[0].natIP)")
echo "VM IP: $VM_IP"

# 4. Add SSH key (if not already added)
gcloud compute instances add-metadata primedata-beta \
  --zone=us-central1-c \
  --metadata-from-file ssh-keys=~/.ssh/github_actions.pub

# 5. Setup environment on VM
gcloud compute ssh primedata-beta --zone=us-central1-c << 'EOF'
cd /opt/primedata
# Create .env.production (see Step 5 above)
EOF

# 6. Trigger application deployment
# Either push code or manually trigger workflow
```

## Troubleshooting

### Infrastructure Deployment Fails

1. Check GitHub Actions logs
2. Verify Workload Identity is working
3. Check service account permissions
4. Review Terraform plan output

### Application Deployment Fails

1. Verify VM is running: `gcloud compute instances list`
2. Check SSH key is added correctly
3. Verify `.env.production` exists on VM
4. Check Docker is installed: `docker --version`
5. Review deployment logs in GitHub Actions

### Services Not Starting

1. SSH to VM and check logs:
   ```bash
   docker-compose -f infra/docker-compose.prod.yml logs
   ```
2. Check environment variables
3. Verify database connection
4. Check container status: `docker ps -a`

## Success Checklist

- [ ] Code pushed to repository
- [ ] Infrastructure deployment completed
- [ ] VM created and accessible
- [ ] SSH key added to VM
- [ ] Environment file created on VM
- [ ] Application deployment completed
- [ ] All services running
- [ ] Health checks passing
- [ ] Can access frontend/backend

## Next Steps After Deployment

1. **Configure Domain** (optional): Point domain to VM IP
2. **Setup SSL/TLS**: Use Let's Encrypt or Cloud Load Balancer
3. **Monitor**: Set up monitoring and alerts
4. **Backup**: Configure automated backups
5. **Scale**: Adjust VM size if needed

---

**Ready to deploy!** Start with Step 1 (push code) and follow the steps above.

