# Cloud SQL PostgreSQL for web-api (auth, users, sessions)
resource "google_sql_database_instance" "web" {
  name             = "shenas-web"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    edition           = "ENTERPRISE"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0"
      }
    }

    backup_configuration {
      enabled = true
    }
  }

  deletion_protection = false
  depends_on          = [google_project_service.apis["sqladmin.googleapis.com"]]
}

resource "google_sql_database" "shenas_net" {
  name     = "shenas_net"
  instance = google_sql_database_instance.web.name
}

resource "google_sql_user" "shenas" {
  name     = "shenas"
  instance = google_sql_database_instance.web.name
  password = var.db_password
}

output "database_ip" {
  value = google_sql_database_instance.web.public_ip_address
}
