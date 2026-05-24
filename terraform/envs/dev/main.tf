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
variable "region" { type = string default = "southamerica-east1" }
variable "image_tag" { type = string default = "latest" }
variable "artifact_registry_repo" { type = string }

locals {
  image_base = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
}

module "iam_api" {
  source             = "../../modules/iam"
  project_id         = var.project_id
  service_account_id = "licitacerta-api-sa"
  display_name       = "LicitaCerta API SA"
  roles = [
    "roles/alloydb.client",
    "roles/storage.objectAdmin",
    "roles/cloudtasks.enqueuer",
    "roles/pubsub.publisher",
    "roles/secretmanager.secretAccessor",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
  ]
}

module "storage" {
  source      = "../../modules/storage"
  project_id  = var.project_id
  region      = var.region
  bucket_name = "licitacerta-docs-dev"
}

module "alloydb" {
  source      = "../../modules/alloydb"
  project_id  = var.project_id
  region      = var.region
  cluster_id  = "licitacerta-dev"
  instance_id = "licitacerta-primary-dev"
}

module "api_service" {
  source                = "../../modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "licitacerta-api-dev"
  image                 = "${local.image_base}/api:${var.image_tag}"
  service_account_email = module.iam_api.email
  min_instances         = 0
  max_instances         = 5
  memory                = "1Gi"
  env_vars = {
    GCP_PROJECT_ID       = var.project_id
    GCP_REGION           = var.region
    GCS_BUCKET_DOCS      = module.storage.bucket_name
    ALLOYDB_INSTANCE_URI = module.alloydb.connection_name
    DOCUMENT_AI_LOCATION = "us"
  }
}
