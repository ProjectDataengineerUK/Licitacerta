variable "project_id" { type = string }
variable "region" { type = string }
variable "network_name" {
  type    = string
  default = "licitacerta-vpc"
}

resource "google_compute_network" "vpc" {
  project                 = var.project_id
  name                    = var.network_name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  project                  = var.project_id
  name                     = "${var.network_name}-subnet"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = "10.0.0.0/24"
  private_ip_google_access = true
}

# Private service access para AlloyDB
resource "google_compute_global_address" "private_ip" {
  project       = var.project_id
  name          = "${var.network_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_project_iam_member" "service_networking_agent" {
  project = var.project_id
  role    = "roles/servicenetworking.serviceAgent"
  member  = "serviceAccount:service-${var.project_number}@service-networking.iam.gserviceaccount.com"
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
  depends_on              = [google_project_iam_member.service_networking_agent]
}

output "network_id" {
  value = google_compute_network.vpc.id
}

output "network_name" {
  value = google_compute_network.vpc.name
}

output "subnet_id" {
  value = google_compute_subnetwork.subnet.id
}
