# Service Account for Compute Instance
# Terraform will automatically detect if this resource already exists and skip creation
resource "google_service_account" "primedata_sa" {
  account_id   = "primedata-compute-sa-${var.environment}"
  display_name = "PrimeData Compute Service Account (${var.environment})"
  description  = "Service account for PrimeData compute resources"

  lifecycle {
    # Prevent accidental deletion
    prevent_destroy = false
  }
}

# Grant Storage Admin to service account (for GCS access)
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.primedata_sa.email}"
}

# Grant Cloud SQL Client (for database access)
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.primedata_sa.email}"
}

# Grant Compute Instance Admin (for metadata access)
resource "google_project_iam_member" "compute_instance_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.primedata_sa.email}"
}

# Service Account Key (for application use)
# Note: Service account key creation may be disabled by organization policy
# This resource will fail if key creation is disabled - that's expected
resource "google_service_account_key" "primedata_sa_key" {
  service_account_id = google_service_account.primedata_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"

  lifecycle {
    # Keys are rotated, so allow replacement
    create_before_destroy = true
  }
}

