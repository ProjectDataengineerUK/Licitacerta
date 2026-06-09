variable "project_id" { type = string }
variable "region" { type = string }
variable "name_prefix" {
  type    = string
  default = "licitacerta-prod"
}
variable "cloud_run_service_name" { type = string }
variable "domain" { type = string }
variable "rate_limit_requests_per_minute" {
  type    = number
  default = 100
}
variable "ban_duration_sec" {
  type    = number
  default = 300
}
