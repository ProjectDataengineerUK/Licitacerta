variable "project_id" { type = string }
variable "region" { type = string }
variable "bucket_name" { type = string }
variable "kms_key_name" { type = string default = "" }

resource "google_storage_bucket" "docs" {
  project                     = var.project_id
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning { enabled = true }

  lifecycle_rule {
    condition { age = 30 matches_prefix = ["raw/"] }
    action { type = "SetStorageClass" storage_class = "NEARLINE" }
  }

  lifecycle_rule {
    condition { age = 365 matches_prefix = ["raw/"] }
    action { type = "Delete" }
  }

  dynamic "encryption" {
    for_each = var.kms_key_name != "" ? [1] : []
    content { default_kms_key_name = var.kms_key_name }
  }
}

output "bucket_name" {
  value = google_storage_bucket.docs.name
}
