output "api_url" {
  value = module.api_service.service_url
}

output "worker_url" {
  value = module.worker_service.service_url
}

output "web_url" {
  value = module.web_service.service_url
}

output "lb_ip" {
  value       = module.lb_armor.lb_ip
  description = "Apontar api_domain para este IP no DNS"
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
}
