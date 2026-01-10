# PrimeData Infrastructure as Code

This directory contains Terraform configuration for deploying PrimeData infrastructure on GCP.

## Prerequisites

1. **GCP Account** with billing enabled
2. **Terraform** >= 1.0 installed
3. **Google Cloud SDK** installed and authenticated
4. **Service Account** with required permissions

## Setup

### 1. Authenticate with GCP

```bash
gcloud auth login
gcloud auth application-default login
```

### 2. Set Project

```bash
gcloud config set project project-f3c8a334-a3f2-4f66-a06
```

### 3. Enable Required APIs

```bash
gcloud services enable \
  compute.googleapis.com \
  sqladmin.googleapis.com \
  storage-component.googleapis.com \
  iam.googleapis.com
```

### 4. Initialize Terraform

```bash
cd infra/terraform
terraform init
```

### 5. Review Plan

```bash
terraform plan
```

### 6. Apply Configuration

```bash
terraform apply
```

## Idempotency & Existing Resources

**Terraform is inherently idempotent** - it will:
- ✅ **Skip creation** if resources already exist (detected via state)
- ✅ **Update** resources if configuration changed
- ✅ **No duplicates** - resources are identified by unique names/IDs

### Working with Existing Resources

If resources already exist (created manually or from previous runs):

**Option 1: Import into Terraform State (Recommended)**
```bash
# Import existing VM
terraform import google_compute_instance.primedata_vm \
  projects/project-f3c8a334-a3f2-4f66-a06/zones/us-central1-c/instances/primedata-beta

# Import existing service account
terraform import google_service_account.primedata_sa \
  projects/project-f3c8a334-a3f2-4f66-a06/serviceAccounts/primedata-compute-sa-beta@project-f3c8a334-a3f2-4f66-a06.iam.gserviceaccount.com
```

**Option 2: Let Terraform Detect (Automatic)**
- Terraform will detect conflicts and show an error
- You can then import or rename resources

**Option 3: Use Data Sources**
- Data sources allow referencing existing resources
- See `data.tf` for examples

### Resource Naming

Resources use unique names with environment suffix:
- VM: `primedata-beta`
- Service Account: `primedata-compute-sa-beta`
- Firewall Rules: `primedata-allow-http-beta`, etc.

This prevents conflicts with existing resources.

## Variables

Create a `terraform.tfvars` file to customize:

```hcl
project_id = "project-f3c8a334-a3f2-4f66-a06"
region     = "us-central1"
zone       = "us-central1-c"
vm_machine_type = "e2-medium"
vm_disk_size    = 50
environment     = "beta"
check_existing_resources = true
```

## Outputs

After applying, Terraform will output:

- `vm_external_ip`: External IP of the VM
- `vm_internal_ip`: Internal IP of the VM
- `service_account_email`: Service account email
- `database_connection_name`: Cloud SQL connection name

## Remote State (Optional)

To use remote state with GCS:

1. Create a bucket for Terraform state:
```bash
gsutil mb gs://primedata-terraform-state
```

2. Uncomment the backend configuration in `main.tf`

3. Re-initialize:
```bash
terraform init -migrate-state
```

## Multi-Cloud Portability

This Terraform configuration can be adapted for:

- **AWS**: Use `aws` provider, replace Compute Engine with EC2
- **Azure**: Use `azurerm` provider, replace with Azure VMs
- **On-Premises**: Use `null` provider or local execution

Key changes needed:
- Provider configuration
- Resource types (EC2 vs Compute Engine)
- Networking (VPC vs VNet)
- Storage (S3 vs GCS vs Blob Storage)

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all infrastructure. Make sure you have backups!

## Troubleshooting

### Resource Already Exists Error

If you get "resource already exists":
1. Import the resource: `terraform import <resource_type>.<name> <resource_id>`
2. Or change the resource name in variables

### State Lock Issues

If Terraform state is locked:
```bash
# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

### Plan Shows No Changes

This is normal! Terraform is idempotent - if resources match desired state, no changes are needed.
