# Note: Buckets are already created manually
# This file documents the bucket configuration

# Buckets that should exist:
# - primedata-raw
# - primedata-processed
# - primedata-exports

# If you want to manage buckets via Terraform, uncomment below:

# resource "google_storage_bucket" "primedata_raw" {
#   name          = "primedata-raw"
#   location      = "US"
#   force_destroy = false
# 
#   uniform_bucket_level_access = true
# 
#   versioning {
#     enabled = true
#   }
# }
# 
# resource "google_storage_bucket" "primedata_processed" {
#   name          = "primedata-processed"
#   location      = "US"
#   force_destroy = false
# 
#   uniform_bucket_level_access = true
# 
#   versioning {
#     enabled = true
#   }
# }
# 
# resource "google_storage_bucket" "primedata_exports" {
#   name          = "primedata-exports"
#   location      = "US"
#   force_destroy = false
# 
#   uniform_bucket_level_access = true
# 
#   versioning {
#     enabled = true
#   }
# }

# Note: Buckets are manually created and referenced by name
# Data sources are not used to avoid permission issues during Terraform plan
# Bucket names are hardcoded in outputs.tf

