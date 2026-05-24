variable "project_id" { type = string }
variable "region" { type = string }
variable "instance_name" { type = string }
variable "db_name" {
  type    = string
  default = "licitacerta"
}
variable "tier" {
  type    = string
  default = "db-g1-small"
}

resource "google_sql_database_instance" "main" {
  project          = var.project_id
  name             = var.instance_name
  region           = var.region
  database_version = "POSTGRES_15"

  settings {
    tier = var.tier

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }

    ip_configuration {
      ipv4_enabled = false
      ssl_mode     = "ENCRYPTED_ONLY"
      psc_config {
        psc_enabled               = true
        allowed_consumer_projects = [var.project_id]
      }
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "db" {
  project  = var.project_id
  instance = google_sql_database_instance.main.name
  name     = var.db_name
}

resource "google_sql_user" "iam_sa" {
  project  = var.project_id
  instance = google_sql_database_instance.main.name
  name     = "licitacerta-api-sa"
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

output "connection_name" {
  value = google_sql_database_instance.main.connection_name
}

output "instance_name" {
  value = google_sql_database_instance.main.name
}
