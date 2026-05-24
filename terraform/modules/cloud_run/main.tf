variable "project_id" { type = string }
variable "region" { type = string }
variable "service_name" { type = string }
variable "image" { type = string }
variable "service_account_email" { type = string }
variable "env_vars" { type = map(string) default = {} }
variable "secrets" {
  type = list(object({ name = string, secret = string, version = string }))
  default = []
}
variable "min_instances" { type = number default = 0 }
variable "max_instances" { type = number default = 10 }
variable "memory" { type = string default = "512Mi" }
variable "cpu" { type = string default = "1" }

resource "google_cloud_run_v2_service" "svc" {
  project  = var.project_id
  location = var.region
  name     = var.service_name

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      resources {
        limits   = { memory = var.memory, cpu = var.cpu }
        cpu_idle = true
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.value.name
          value_source {
            secret_key_ref {
              secret  = env.value.secret
              version = env.value.version
            }
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

output "service_url" {
  value = google_cloud_run_v2_service.svc.uri
}
