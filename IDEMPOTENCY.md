# Idempotency & Existing Resources Guide

This document explains how PrimeData infrastructure handles existing resources and ensures idempotent operations.

## Overview

**Idempotency** means running the same operation multiple times produces the same result without creating duplicates or errors. All PrimeData infrastructure components are designed to be idempotent.

## Terraform Idempotency

### How Terraform Handles Existing Resources

Terraform is **inherently idempotent**:

1. **State Management**: Terraform tracks all resources in state
2. **Comparison**: Compares desired state (code) with actual state
3. **Skip Creation**: If resource exists and matches, no action taken
4. **Update Only**: Only updates resources that differ
5. **No Duplicates**: Resources identified by unique names/IDs

### Resource Naming Strategy

All resources use unique names with environment suffix:
- VM: `primedata-beta`
- Service Account: `primedata-compute-sa-beta`
- Firewall Rules: `primedata-allow-http-beta`

This prevents conflicts with existing resources.

### Handling Existing Resources

**Scenario 1: Resource Already in State**
- ✅ Terraform detects it exists
- ✅ Skips creation
- ✅ Updates if configuration changed

**Scenario 2: Resource Exists but Not in State**
- ⚠️ Terraform will try to create
- ⚠️ GCP will return "already exists" error
- ✅ **Solution**: Import resource into state

```bash
# Import existing VM
terraform import google_compute_instance.primedata_vm \
  projects/project-f3c8a334-a3f2-4f66-a06/zones/us-central1-c/instances/primedata-beta
```

**Scenario 3: Resource Exists with Different Name**
- ✅ No conflict - Terraform creates new resource
- ✅ Both resources coexist

### Lifecycle Rules

Resources have lifecycle rules for safety:

```hcl
lifecycle {
  create_before_destroy = true  # Prevents downtime
  ignore_changes = [metadata_startup_script]  # Ignores changes after creation
  prevent_destroy = false  # Allows deletion if needed
}
```

## GitHub Actions Idempotency

### Infrastructure Deployment

The `deploy-infra.yml` workflow:

1. **Terraform Plan**: Shows what will change (idempotent)
2. **Terraform Apply**: Only applies changes (idempotent)
3. **No Duplicates**: Terraform handles this automatically

**If resources exist:**
- Plan shows "no changes" or only differences
- Apply skips existing resources
- No errors or duplicates

### Application Deployment

The `deploy-app.yml` workflow uses idempotent operations:

```bash
# Docker network (idempotent)
docker network create primedata-network 2>/dev/null || echo "Network already exists"

# Docker Compose (idempotent)
docker-compose up -d --build --remove-orphans
# - up -d: Starts containers if not running, no-op if running
# - --build: Rebuilds images if changed, skips if unchanged
# - --remove-orphans: Cleans up old containers

# Database migrations (idempotent)
alembic upgrade head
# Alembic tracks applied migrations, skips already applied
```

## Docker Compose Idempotency

### Container Management

Docker Compose commands are idempotent:

- **`up -d`**: 
  - Starts stopped containers
  - No-op if containers already running
  - Creates containers if they don't exist

- **`pull`**: 
  - Updates images if newer version available
  - No-op if images are current

- **`build`**: 
  - Rebuilds images if Dockerfile changed
  - Uses cache if unchanged

- **`exec`**: 
  - Runs command in existing container
  - Fails gracefully if container doesn't exist

### Volume Management

Volumes are persistent:
- ✅ Data persists across container restarts
- ✅ No data loss on `up -d`
- ✅ Volumes created once, reused forever

### Network Management

```bash
docker network create primedata-network 2>/dev/null || echo "Network already exists"
```

This command:
- ✅ Creates network if it doesn't exist
- ✅ Skips silently if it exists
- ✅ No errors or duplicates

## Database Migrations

Alembic migrations are idempotent:

1. **Migration Tracking**: Tracks applied migrations in database
2. **Skip Applied**: Automatically skips already applied migrations
3. **Safe to Re-run**: Can run `alembic upgrade head` multiple times safely

```bash
# Safe to run multiple times
alembic upgrade head
# First run: Applies pending migrations
# Second run: "No migrations to apply"
```

## Best Practices

### 1. Always Use Terraform State

- ✅ Use remote state (GCS) for team collaboration
- ✅ Never delete `.tfstate` files
- ✅ Commit state to version control (if using local state)

### 2. Import Existing Resources

If resources exist before Terraform:
```bash
# Import into state
terraform import <resource_type>.<name> <resource_id>

# Verify
terraform plan  # Should show "no changes"
```

### 3. Use Unique Names

- ✅ Include environment in resource names
- ✅ Use project prefixes
- ✅ Avoid generic names

### 4. Test Idempotency

```bash
# Run apply twice - second should show "no changes"
terraform apply
terraform apply  # Should show: "No changes. Infrastructure is up-to-date."
```

### 5. Handle Errors Gracefully

Scripts use `|| true` or `2>/dev/null` for idempotent operations:
```bash
docker network create primedata-network 2>/dev/null || echo "Exists"
```

## Troubleshooting

### "Resource Already Exists" Error

**Problem**: Terraform tries to create resource that exists

**Solution**:
```bash
# Import the resource
terraform import <resource_type>.<name> <resource_id>

# Or rename the resource in Terraform
```

### "No Changes" in Plan

**This is normal!** Terraform is idempotent - if everything matches desired state, no changes needed.

### Duplicate Resources

**Problem**: Multiple resources with same name

**Solution**:
1. Check Terraform state: `terraform state list`
2. Remove duplicates: `terraform state rm <resource>`
3. Import correct resource

### Container Won't Start

**Problem**: Container exists but won't start

**Solution**:
```bash
# Remove and recreate (idempotent)
docker-compose down
docker-compose up -d
```

## Summary

✅ **Terraform**: Inherently idempotent via state management
✅ **Docker Compose**: Idempotent via `up -d` and container names
✅ **Database Migrations**: Idempotent via Alembic tracking
✅ **GitHub Actions**: Uses idempotent operations throughout
✅ **Scripts**: Handle existing resources gracefully

**Result**: You can run deployments multiple times safely without creating duplicates or errors!

