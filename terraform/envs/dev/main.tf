terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
  backend "gcs" {
    bucket = "licitacerta-tfstate-dev"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" { type = string }
variable "artifact_registry_repo" { type = string }
variable "region" {
  type    = string
  default = "southamerica-east1"
}
variable "image_tag" {
  type    = string
  default = "placeholder"
}
variable "enable_alloydb" {
  type    = bool
  default = false
}

locals {
  image_base        = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
  placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello:latest"
  api_image         = var.image_tag == "placeholder" ? local.placeholder_image : "${local.image_base}/api:${var.image_tag}"
  worker_image      = var.image_tag == "placeholder" ? local.placeholder_image : "${local.image_base}/worker:${var.image_tag}"
  web_image         = var.image_tag == "placeholder" ? local.placeholder_image : "${local.image_base}/web:${var.image_tag}"
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

# Artifact Registry (já existe — importado)
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
  description = "LicitaCerta agent runs and analytics"
  depends_on  = [google_project_service.apis]
}

resource "google_bigquery_table" "agent_runs" {
  project             = var.project_id
  dataset_id          = google_bigquery_dataset.licitacerta.dataset_id
  table_id            = "agent_runs"
  deletion_protection = false

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

# Secret Manager — só ANTHROPIC (Gemini via Vertex AI nativo, sem chave)
resource "google_secret_manager_secret" "anthropic_api_key" {
  project   = var.project_id
  secret_id = "ANTHROPIC_API_KEY"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# IAM — gerenciado via bootstrap (SA e bindings criados fora do CI)
# O WIF SA de deploy não tem resourcemanager.projects.getIamPolicy.
data "google_service_account" "api_sa" {
  account_id = "licitacerta-api-sa"
  project    = var.project_id
}

# Storage
module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  region      = var.region
  bucket_name = "licitacerta-docs-dev"
}

# Cloud Run — API
module "api_service" {
  source                = "../../modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "licitacerta-api-dev"
  image                 = local.api_image
  service_account_email = data.google_service_account.api_sa.email
  min_instances         = 0
  max_instances         = 5
  memory                = "1Gi"
  allow_public_access   = true
  env_vars = {
    GCP_PROJECT_ID       = var.project_id
    GCP_REGION           = var.region
    GCS_BUCKET_DOCS      = module.storage.bucket_name
    BQ_DATASET           = google_bigquery_dataset.licitacerta.dataset_id
    DOCUMENT_AI_LOCATION = "us"
  }
  secrets = [
    { name = "ANTHROPIC_API_KEY", secret = "ANTHROPIC_API_KEY", version = "latest" },
  ]
  depends_on = [google_project_service.apis]
}

# Cloud Run — Worker
module "worker_service" {
  source                = "../../modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "licitacerta-worker-dev"
  image                 = local.worker_image
  service_account_email = data.google_service_account.api_sa.email
  min_instances         = 0
  max_instances         = 3
  memory                = "2Gi"
  env_vars = {
    GCP_PROJECT_ID  = var.project_id
    GCP_REGION      = var.region
    GCS_BUCKET_DOCS = module.storage.bucket_name
    BQ_DATASET      = google_bigquery_dataset.licitacerta.dataset_id
    WORKER_MODULE   = "src.workers.agents_worker"
  }
  secrets = [
    { name = "ANTHROPIC_API_KEY", secret = "ANTHROPIC_API_KEY", version = "latest" },
  ]
  depends_on = [google_project_service.apis]
}

# Cloud Run — Web
module "web_service" {
  source                = "../../modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "licitacerta-web-dev"
  image                 = local.web_image
  service_account_email = data.google_service_account.api_sa.email
  min_instances         = 0
  max_instances         = 3
  memory                = "512Mi"
  allow_public_access = true
  env_vars = {
    API_INTERNAL_URL                 = module.api_service.service_url
    NEXT_PUBLIC_FIREBASE_PROJECT_ID  = var.project_id
    NEXT_PUBLIC_AUTH_BYPASS          = "1"
  }
  depends_on = [google_project_service.apis]
}

# Outputs
output "api_url" {
  value = module.api_service.service_url
}

output "worker_url" {
  value = module.worker_service.service_url
}

output "web_url" {
  value = module.web_service.service_url
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
}
