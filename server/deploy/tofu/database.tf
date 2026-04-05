# Cloud SQL PostgreSQL for shenas.net auth (Better Auth sessions/users)
resource "google_sql_database_instance" "shenas_net" {
  name             = "shenas-web"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled    = false
      private_network = "projects/${var.project}/global/networks/default"
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
  instance = google_sql_database_instance.shenas_net.name
}

resource "google_sql_user" "shenas_net" {
  name     = "shenas"
  instance = google_sql_database_instance.shenas_net.name
  password = var.db_password
}
