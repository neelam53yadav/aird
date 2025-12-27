# Compute Engine Instance
# Terraform will automatically detect if this resource already exists and skip creation
resource "google_compute_instance" "primedata_vm" {
  name         = var.vm_name
  machine_type = var.vm_machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.vm_disk_size
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    
    dynamic "access_config" {
      for_each = var.enable_public_ip ? [1] : []
      content {
        // Ephemeral public IP
      }
    }
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = file("${path.module}/scripts/startup.sh")

  tags = ["primedata", "http-server", "https-server"]

  service_account {
    email  = google_service_account.primedata_sa.email
    scopes = ["cloud-platform"]
  }

  lifecycle {
    create_before_destroy = true
    # Ignore changes to startup script after initial creation
    ignore_changes = [metadata_startup_script]
  }
}

# Firewall Rules
resource "google_compute_firewall" "allow_http" {
  name    = "primedata-allow-http-${var.environment}"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "8080", "8000", "3000", "6333", "6334"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server"]
  
  description = "Allow HTTP traffic for PrimeData services"
}

resource "google_compute_firewall" "allow_https" {
  name    = "primedata-allow-https-${var.environment}"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https-server"]
  
  description = "Allow HTTPS traffic for PrimeData services"
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "primedata-allow-ssh-${var.environment}"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["primedata"]
  
  description = "Allow SSH access for deployment"
}

