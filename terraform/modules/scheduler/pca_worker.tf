variable "pca_worker_url" {
  description = "Cloud Run URL do pca_worker"
  type        = string
}

variable "worker_sa_email" {
  description = "Service account email para o worker"
  type        = string
}

resource "google_cloud_scheduler_job" "pca_worker_weekly" {
  name             = "pca-worker-weekly"
  description      = "Ingestão semanal do PCA e geração de previsões"
  schedule         = "0 2 * * 0"
  time_zone        = "America/Sao_Paulo"
  attempt_deadline = "1800s"

  http_target {
    uri         = var.pca_worker_url
    http_method = "POST"
    body        = base64encode("{}")
    headers     = { "Content-Type" = "application/json" }
    oidc_token {
      service_account_email = var.worker_sa_email
    }
  }

  retry_config {
    retry_count = 2
  }
}

resource "google_cloud_scheduler_job" "pca_worker_daily_jan" {
  name             = "pca-worker-daily-jan"
  description      = "Ingestão diária do PCA em janeiro"
  schedule         = "0 3 * 1 *"
  time_zone        = "America/Sao_Paulo"
  attempt_deadline = "1800s"

  http_target {
    uri         = var.pca_worker_url
    http_method = "POST"
    body        = base64encode("{}")
    headers     = { "Content-Type" = "application/json" }
    oidc_token {
      service_account_email = var.worker_sa_email
    }
  }

  retry_config {
    retry_count = 2
  }
}
