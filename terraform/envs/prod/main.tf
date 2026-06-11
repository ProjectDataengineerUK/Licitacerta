terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
  backend "gcs" {
    bucket = "licitacerta-prod-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  image_base        = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
  placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello:latest"
  api_image         = var.image_tag == "placeholder" ? local.placeholder_image : "${local.image_base}/api:${var.image_tag}"
  worker_image      = var.image_tag == "placeholder" ? local.placeholder_image : "${local.image_base}/worker:${var.image_tag}"
  web_image         = var.image_tag == "placeholder" ? local.placeholder_image : "${local.image_base}/web:${var.image_tag}"
  env               = "prod"
}

# APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "alloydb.googleapis.com",
    "storage.googleapis.com",
    "cloudtasks.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "monitoring.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "aiplatform.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Artifact Registry
resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# BigQuery
resource "google_bigquery_dataset" "licitacerta" {
  project     = var.project_id
  dataset_id  = "licitacerta"
  location    = var.region
  description = "LicitaCerta agent runs and analytics — prod"
  depends_on  = [google_project_service.apis]
}

resource "google_bigquery_table" "agent_runs" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.licitacerta.dataset_id
  table_id            = "agent_runs"
  deletion_protection = true

  schema = jsonencode([
    { name = "run_id",        type = "STRING",    mode = "REQUIRED" },
    { name = "tenant_id",     type = "STRING",    mode = "REQUIRED" },
    { name = "agent_name",    type = "STRING",    mode = "REQUIRED" },
    { name = "model_used",    type = "STRING",    mode = "NULLABLE" },
    { name = "input_tokens",  type = "INTEGER",   mode = "NULLABLE" },
    { name = "output_tokens", type = "INTEGER",   mode = "NULLABLE" },
    { name = "cost_usd",      type = "FLOAT",     mode = "NULLABLE" },
    { name = "currency",      type = "STRING",    mode = "NULLABLE" },
    { name = "duration_ms",   type = "INTEGER",   mode = "NULLABLE" },
    { name = "success",       type = "BOOLEAN",   mode = "NULLABLE" },
    { name = "created_at",    type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

# Secret Manager — secrets (valores definidos fora do Terraform)
locals {
  secrets = toset([
    "ANTHROPIC_API_KEY",
    "DATABASE_URL",
    "SECRET_KEY",
  ])
}

resource "google_secret_manager_secret" "app_secrets" {
  for_each  = local.secrets
  project   = var.project_id
  secret_id = each.value
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# IAM — SA de runtime (criado via bootstrap)
data "google_service_account" "api_sa" {
  account_id = "licitacerta-api-sa"
  project    = var.project_id
}

# Storage
module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  region      = var.region
  bucket_name = "licitacerta-docs-prod"
}

# VPC — necessário para AlloyDB
module "vpc" {
  source         = "../../modules/vpc"
  project_id     = var.project_id
  project_number = var.project_number
  region         = var.region
  network_name   = "licitacerta-prod-vpc"
  depends_on     = [google_project_service.apis]
}

# AlloyDB — HA Regional com PITR
module "alloydb" {
  source                    = "../../modules/alloydb"
  project_id                = var.project_id
  region                    = var.region
  cluster_id                = "licitacerta-prod"
  instance_id               = "licitacerta-prod-primary"
  network_id                = module.vpc.network_id
  availability_type         = "REGIONAL"
  pitr_enabled              = true
  pitr_recovery_window_days = 14
  cpu_count                 = 2
  initial_password          = var.alloydb_initial_password
  depends_on                = [module.vpc]
}

# Cloud Run — API (min=1 para prod, CPU=2)
module "api_service" {
  source                = "../../modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "licitacerta-api-prod"
  image                 = local.api_image
  service_account_email = data.google_service_account.api_sa.email
  min_instances         = 1
  max_instances         = 10
  cpu                   = "2"
  memory                = "2Gi"
  allow_public_access   = true
  env_vars = {
    GCP_PROJECT_ID       = var.project_id
    GCP_REGION           = var.region
    GCS_BUCKET_DOCS      = module.storage.bucket_name
    BQ_DATASET           = google_bigquery_dataset.licitacerta.dataset_id
    DOCUMENT_AI_LOCATION = "us"
    ENVIRONMENT          = "prod"
  }
  secrets = [
    { name = "ANTHROPIC_API_KEY", secret = "ANTHROPIC_API_KEY", version = "latest" },
    { name = "DATABASE_URL",      secret = "DATABASE_URL",      version = "latest" },
    { name = "SECRET_KEY",        secret = "SECRET_KEY",        version = "latest" },
  ]
  depends_on = [google_project_service.apis, google_secret_manager_secret.app_secrets]
}

# Cloud Run — Worker (min=1, CPU=2, memória maior)
module "worker_service" {
  source                = "../../modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "licitacerta-worker-prod"
  image                 = local.worker_image
  service_account_email = data.google_service_account.api_sa.email
  min_instances         = 1
  max_instances         = 5
  cpu                   = "2"
  memory                = "4Gi"
  env_vars = {
    GCP_PROJECT_ID  = var.project_id
    GCP_REGION      = var.region
    GCS_BUCKET_DOCS = module.storage.bucket_name
    BQ_DATASET      = google_bigquery_dataset.licitacerta.dataset_id
    WORKER_MODULE   = "src.workers.agents_worker"
    ENVIRONMENT     = "prod"
  }
  secrets = [
    { name = "ANTHROPIC_API_KEY", secret = "ANTHROPIC_API_KEY", version = "latest" },
    { name = "DATABASE_URL",      secret = "DATABASE_URL",      version = "latest" },
    { name = "SECRET_KEY",        secret = "SECRET_KEY",        version = "latest" },
  ]
  depends_on = [google_project_service.apis, google_secret_manager_secret.app_secrets]
}

# Cloud Run — Web
module "web_service" {
  source                = "../../modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "licitacerta-web-prod"
  image                 = local.web_image
  service_account_email = data.google_service_account.api_sa.email
  min_instances         = 1
  max_instances         = 5
  memory                = "512Mi"
  allow_public_access   = true
  env_vars = {
    API_INTERNAL_URL                = module.api_service.service_url
    NEXT_PUBLIC_FIREBASE_PROJECT_ID = var.project_id
    ENVIRONMENT                     = "prod"
  }
  depends_on = [google_project_service.apis]
}

# Cloud Armor + Global LB para a API
module "lb_armor" {
  source                 = "../../modules/lb_armor"
  project_id             = var.project_id
  region                 = var.region
  name_prefix            = "licitacerta-prod"
  cloud_run_service_name = module.api_service.service_url != "" ? "licitacerta-api-prod" : "licitacerta-api-prod"
  domain                 = var.api_domain
  depends_on             = [module.api_service, google_project_service.apis]
}

# Uptime check
resource "google_monitoring_uptime_check_config" "api_health" {
  project      = var.project_id
  display_name = "API Prod — Health Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path    = "/health"
    port    = "443"
    use_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      host       = var.api_domain
      project_id = var.project_id
    }
  }
}

# Alerting policy — API indisponível por 3 min
resource "google_monitoring_alert_policy" "api_uptime" {
  project      = var.project_id
  display_name = "API Prod — Uptime < 100%"
  combiner     = "OR"

  conditions {
    display_name = "Uptime check failing"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\""
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "180s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_FRACTION_TRUE"
      }
    }
  }

  notification_channels = []
}
