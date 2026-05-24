variable "project_id" { type = string }
variable "organization_id" { type = string default = "" }

# Security Command Center Premium — enables threat detection and posture management
resource "google_scc_project_notification_config" "alerts" {
  project          = var.project_id
  config_id        = "licitacerta-scc-alerts"
  description      = "LicitaCerta SCC threat alerts"
  pubsub_topic     = "projects/${var.project_id}/topics/scc-alerts"
  streaming_config {
    filter = "state = \"ACTIVE\""
  }
}

# Cloud Armor security policy
resource "google_compute_security_policy" "api_policy" {
  project = var.project_id
  name    = "licitacerta-api-policy"

  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr { expression = "evaluatePreconfiguredExpr('sqli-stable')" }
    }
    description = "Block SQL injection"
  }

  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr { expression = "evaluatePreconfiguredExpr('xss-stable')" }
    }
    description = "Block XSS"
  }

  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
    description = "Default allow"
  }
}

# VPC Service Controls — org-level, optional
variable "enable_vpc_sc" { type = bool default = false }

output "security_policy_name" {
  value = google_compute_security_policy.api_policy.name
}
