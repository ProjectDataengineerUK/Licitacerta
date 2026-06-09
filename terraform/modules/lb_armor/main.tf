resource "google_compute_region_network_endpoint_group" "api_neg" {
  project               = var.project_id
  name                  = "${var.name_prefix}-api-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = var.cloud_run_service_name
  }
}

resource "google_compute_security_policy" "armor" {
  project = var.project_id
  name    = "${var.name_prefix}-armor"

  rule {
    action      = "throttle"
    priority    = "1000"
    description = "Rate limit ${var.rate_limit_requests_per_minute} req/min per IP"
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = var.rate_limit_requests_per_minute
        interval_sec = 60
      }
      ban_threshold {
        count        = var.rate_limit_requests_per_minute * 10
        interval_sec = 600
      }
      ban_duration_sec = var.ban_duration_sec
    }
  }

  rule {
    action      = "allow"
    priority    = "2147483647"
    description = "Default allow"
    match {
      versioned_expr = "SRC_IPS_V1"
      config { src_ip_ranges = ["*"] }
    }
  }
}

resource "google_compute_backend_service" "api" {
  project               = var.project_id
  name                  = "${var.name_prefix}-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"
  security_policy       = google_compute_security_policy.armor.id

  backend {
    group = google_compute_region_network_endpoint_group.api_neg.id
  }
}

resource "google_compute_url_map" "api" {
  project         = var.project_id
  name            = "${var.name_prefix}-urlmap"
  default_service = google_compute_backend_service.api.id
}

resource "google_compute_managed_ssl_certificate" "api" {
  project = var.project_id
  name    = "${var.name_prefix}-cert"

  managed {
    domains = [var.domain]
  }
}

resource "google_compute_target_https_proxy" "api" {
  project          = var.project_id
  name             = "${var.name_prefix}-https-proxy"
  url_map          = google_compute_url_map.api.id
  ssl_certificates = [google_compute_managed_ssl_certificate.api.id]
}

resource "google_compute_global_forwarding_rule" "api" {
  project               = var.project_id
  name                  = "${var.name_prefix}-fwd-443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  target                = google_compute_target_https_proxy.api.id
  port_range            = "443"
  ip_protocol           = "TCP"
}

output "lb_ip" {
  value = google_compute_global_forwarding_rule.api.ip_address
}

output "security_policy_id" {
  value = google_compute_security_policy.armor.id
}
