# GitHub Actions Setup Guide

## ✅ Workload Identity Federation Setup (Complete)

Your GitHub Actions is configured to use **Workload Identity Federation**, which is more secure than service account keys.

### Configuration Details

- **Project ID**: `project-f3c8a334-a3f2-4f66-a06`
- **Project Number**: `890841479962`
- **Workload Identity Pool**: `github-pool`
- **OIDC Provider**: `github-provider`
- **Service Account**: `github-actions@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com`

### Workload Identity Provider Path

```
projects/890841479962/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

## Required GitHub Secrets

You only need to add these secrets to GitHub:

### 1. VM_USERNAME

**Value**: Your GCP username (from Cloud Shell)
- Example: `neelamvivaan23`

**How to get it:**
```bash
echo $USER
```

### 2. VM_SSH_KEY

**Value**: Your private SSH key for VM access

**How to create:**
```bash
# Generate SSH key
ssh-keygen -t rsa -b 4096 -C "github-actions-deploy" -f ~/.ssh/github_actions_deploy

# Add public key to VM (after VM is created)
gcloud compute instances add-metadata primedata-beta \
  --zone=us-central1-c \
  --metadata-from-file ssh-keys=~/.ssh/github_actions_deploy.pub

# Copy private key content to GitHub secret
cat ~/.ssh/github_actions_deploy
```

## Adding Secrets to GitHub

1. Go to your repository: https://github.com/neelam53yadav/aird
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:
   - Name: `VM_USERNAME`, Value: `neelamvivaan23`
   - Name: `VM_SSH_KEY`, Value: (paste private key content)

## Fixing OIDC Provider (If Needed)

If the OIDC provider wasn't created correctly, run this script:

```bash
# In Cloud Shell
chmod +x infra/scripts/fix-oidc-provider.sh
./infra/scripts/fix-oidc-provider.sh
```

## How It Works

1. **GitHub Actions** requests an OIDC token from GitHub
2. **Workload Identity Federation** validates the token
3. **GCP** grants temporary access to the service account
4. **No service account keys** are stored or needed!

## Benefits

✅ **More Secure**: No long-lived service account keys
✅ **Automatic**: No manual key rotation needed
✅ **Auditable**: Better tracking of who accessed what
✅ **Policy Compliant**: Works with organization policies that block key creation

## Testing

After adding secrets, test by:

1. Push a small change to trigger workflow
2. Check GitHub Actions tab
3. Verify authentication succeeds
4. Check that Terraform/Deployment runs

## Troubleshooting

### Authentication Fails

- Verify Workload Identity Pool exists:
  ```bash
  gcloud iam workload-identity-pools describe github-pool \
    --project=project-f3c8a334-a3f2-4f66-a06 \
    --location="global"
  ```

- Verify OIDC Provider exists:
  ```bash
  gcloud iam workload-identity-pools providers describe github-provider \
    --project=project-f3c8a334-a3f2-4f66-a06 \
    --location="global" \
    --workload-identity-pool=github-pool
  ```

- Check service account binding:
  ```bash
  gcloud iam service-accounts get-iam-policy \
    github-actions@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com
  ```

### SSH Connection Fails

- Verify SSH key is added to VM:
  ```bash
  gcloud compute instances describe primedata-beta \
    --zone=us-central1-c \
    --format="value(metadata.items[0].value)"
  ```

- Test SSH manually:
  ```bash
  gcloud compute ssh primedata-beta --zone=us-central1-c
  ```

## Workflow Files Updated

✅ `.github/workflows/deploy-infra.yml` - Uses Workload Identity
✅ `.github/workflows/deploy-app.yml` - Uses Workload Identity
✅ `.github/workflows/ci.yml` - No GCP auth needed

## Next Steps

1. ✅ Workload Identity Federation configured
2. ✅ Workflows updated
3. ⏳ Add `VM_USERNAME` secret to GitHub
4. ⏳ Add `VM_SSH_KEY` secret to GitHub
5. ⏳ Test workflows by pushing code

---

**You're all set!** Once you add the two secrets (`VM_USERNAME` and `VM_SSH_KEY`), your workflows will work automatically.

