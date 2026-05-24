variable "project_id" { type = string }
variable "region" { type = string }
variable "cluster_id" { type = string }
variable "instance_id" { type = string }
variable "db_name" { type = string default = "licitacerta" }
variable "cpu_count" { type = number default = 2 }

resource "google_alloydb_cluster" "main" {
  project    = var.project_id
  location   = var.region
  cluster_id = var.cluster_id

  initial_user {
    password = ""  # IAM auth only — no password
  }

  automated_backup_policy {
    enabled = true
    weekly_schedule {
      days_of_week = ["SUNDAY"]
      start_times { hours = 3 minutes = 0 seconds = 0 nanos = 0 }
    }
    quantity_based_retention {
      count = 7
    }
  }

  encryption_config {
    kms_key_name = var.kms_key_name
  }
}

variable "kms_key_name" { type = string default = "" }

resource "google_alloydb_instance" "primary" {
  cluster       = google_alloydb_cluster.main.name
  instance_id   = var.instance_id
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = var.cpu_count
  }
}

output "instance_name" {
  value = google_alloydb_instance.primary.name
}

output "connection_name" {
  value = "${var.project_id}:${var.region}:${var.cluster_id}:${var.instance_id}"
}
