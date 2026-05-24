variable "project_id" { type = string }
variable "service_account_id" { type = string }
variable "display_name" { type = string }

resource "google_service_account" "sa" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = var.display_name
}

# Cloud Run SA roles
variable "roles" {
  type    = list(string)
  default = []
}

resource "google_project_iam_member" "roles" {
  for_each = toset(var.roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.sa.email}"
}

output "email" {
  value = google_service_account.sa.email
}
