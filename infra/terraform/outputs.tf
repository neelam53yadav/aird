output "vm_external_ip" {
  description = "External IP of the VM"
  value       = var.enable_public_ip ? google_compute_instance.primedata_vm.network_interface[0].access_config[0].nat_ip : "N/A (private IP only)"
}

output "vm_internal_ip" {
  description = "Internal IP of the VM"
  value       = google_compute_instance.primedata_vm.network_interface[0].network_ip
}

output "vm_name" {
  description = "VM instance name"
  value       = google_compute_instance.primedata_vm.name
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.primedata_sa.email
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = "${var.project_id}:${var.region}:${var.db_instance_name}"
}

output "bucket_names" {
  description = "GCS bucket names (manually created buckets)"
  value = {
    raw       = "primedata-raw"
    processed = "primedata-processed"
    exports   = "primedata-exports"
  }
}

