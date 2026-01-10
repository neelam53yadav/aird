variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "project-f3c8a334-a3f2-4f66-a06"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-c"
}

variable "db_instance_name" {
  description = "Cloud SQL instance name (already exists)"
  type        = string
  default     = "primedata-postgres"
}

variable "vm_machine_type" {
  description = "VM machine type"
  type        = string
  default     = "e2-medium"
}

variable "vm_disk_size" {
  description = "VM disk size in GB"
  type        = number
  default     = 50
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "beta"
}

variable "vm_name" {
  description = "VM instance name"
  type        = string
  default     = "primedata-beta"
}

variable "enable_public_ip" {
  description = "Enable public IP for VM"
  type        = bool
  default     = true
}

variable "check_existing_resources" {
  description = "Check for existing resources before creating (for idempotency)"
  type        = bool
  default     = true
}

