variable "project_id" { type = string }
variable "project_number" { type = string }
variable "artifact_registry_repo" { type = string }

variable "region" {
  type    = string
  default = "southamerica-east1"
}

variable "image_tag" {
  type    = string
  default = "placeholder"
}

variable "alloydb_initial_password" {
  type      = string
  sensitive = true
}
