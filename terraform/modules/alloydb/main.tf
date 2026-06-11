variable "project_id" { type = string }
variable "region" { type = string }
variable "cluster_id" { type = string }
variable "instance_id" { type = string }
variable "network_id" { type = string }
variable "db_name" {
  type    = string
  default = "licitacerta"
}
variable "cpu_count" {
  type    = number
  default = 2
}
variable "availability_type" {
  type    = string
  default = "ZONAL"
  validation {
    condition     = contains(["ZONAL", "REGIONAL"], var.availability_type)
    error_message = "availability_type must be ZONAL or REGIONAL."
  }
}
variable "pitr_enabled" {
  type    = bool
  default = false
}
variable "pitr_recovery_window_days" {
  type    = number
  default = 14
}
variable "initial_password" {
  type      = string
  sensitive = true
  default   = ""
}

resource "google_alloydb_cluster" "main" {
  project    = var.project_id
  location   = var.region
  cluster_id = var.cluster_id

  network_config {
    network = var.network_id
  }

  initial_user {
    password = var.initial_password
  }

  automated_backup_policy {
    enabled = true
    weekly_schedule {
      days_of_week = ["SUNDAY"]
      start_times {
        hours   = 3
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
    quantity_based_retention {
      count = 7
    }
  }

  dynamic "continuous_backup_config" {
    for_each = var.pitr_enabled ? [1] : []
    content {
      enabled              = true
      recovery_window_days = var.pitr_recovery_window_days
    }
  }
}

resource "google_alloydb_instance" "primary" {
  cluster           = google_alloydb_cluster.main.name
  instance_id       = var.instance_id
  instance_type     = "PRIMARY"
  availability_type = var.availability_type

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
