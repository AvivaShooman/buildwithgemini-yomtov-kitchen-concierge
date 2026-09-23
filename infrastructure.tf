# ==============================================================================
# YomTov Kitchen Concierge — Complete Cloud Infrastructure as Code (Terraform)
# ==============================================================================
#
# CONTEXT & ARCHITECTURE OVERVIEW:
# ---------------------------------
# YomTov Kitchen Concierge is an agentic culinary and halachic planning application
# built on Google Cloud Vertex AI Agent Platform and Google ADK.
#
# Core Infrastructure Components:
# 1. Vertex AI Agent Platform Reasoning Engine & Memory Bank:
#    - Hosts the ADK Agent (gemini-2.5-flash / gemini-3.1-flash-lite-image)
#    - Connects to Vertex AI Memory Bank for long-term household/allergy memory
#    - Integrates Vertex AI RAG Engine for kosher culinary blog retrieval
# 2. Cloud Firestore (Native Mode):
#    - Stores structured recipe data (19 holiday dishes), warming criteria,
#      liquid evaporation parameters, user ratings, and scaled grocery lists
# 3. Google Cloud Storage (GCS):
#    - Public media bucket hosting recipe datasets, markdown documents, and
#      AI-generated dish/table photography from gemini-3.1-flash-lite-image
# 4. Google Cloud Run:
#    - Serves the custom responsive chat frontend (FastAPI + A2A protocol proxy)
#    - Provides /recipe/{slug} plain-text recipe rendering and A2UI card display
# 5. IAM & Least-Privilege Access:
#    - Dedicated service account with aiplatform.user, datastore.user, storage.objectAdmin
#
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.30"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ------------------------------------------------------------------------------
# Provider Configurations
# ------------------------------------------------------------------------------

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ------------------------------------------------------------------------------
# Input Variables
# ------------------------------------------------------------------------------

variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID where all services are provisioned."
  default     = "qwiklabs-gcp-04-ded35b1abcfb"
}

variable "project_number" {
  type        = string
  description = "The Google Cloud Project Number (used in resource paths)."
  default     = "821049907373"
}

variable "region" {
  type        = string
  description = "The primary Google Cloud region for regional services."
  default     = "us-east1"
}

variable "media_bucket_name" {
  type        = string
  description = "GCS bucket name for recipe assets and AI-generated dish photography."
  default     = "yomtov-kitchen-media-qwiklabs-gcp-04-ded35b1abcfb"
}

variable "frontend_service_name" {
  type        = string
  description = "Cloud Run service name for the web chat frontend."
  default     = "yomtov-kitchen-frontend"
}

variable "service_account_id" {
  type        = string
  description = "Service account ID for YomTov Kitchen Concierge workloads."
  default     = "yomtov-kitchen-sa"
}

variable "artifact_registry_repo_id" {
  type        = string
  description = "Artifact Registry Docker repository ID."
  default     = "yomtov-kitchen-repo"
}

variable "agent_engine_resource_name" {
  type        = string
  description = "Fully qualified Vertex AI Reasoning Engine resource path."
  default     = "projects/821049907373/locations/us-east1/reasoningEngines/5254198832257826816"
}

variable "enable_seeding" {
  type        = bool
  description = "Whether to trigger local-exec scripts to seed Firestore and provision RAG corpus."
  default     = false
}

# ------------------------------------------------------------------------------
# Google Cloud APIs Enablement
# ------------------------------------------------------------------------------

locals {
  required_services = [
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "serviceusage.googleapis.com"
  ]
}

resource "google_project_service" "enabled_services" {
  for_each                   = toset(local.required_services)
  project                    = var.project_id
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

# ------------------------------------------------------------------------------
# IAM Service Account & Roles
# ------------------------------------------------------------------------------

resource "google_service_account" "agent_sa" {
  account_id   = var.service_account_id
  display_name = "YomTov Kitchen Concierge Service Account"
  description  = "Dedicated identity for Vertex AI Agent Engine, Cloud Run frontend, and background workers"
  depends_on   = [google_project_service.enabled_services]
}

locals {
  agent_roles = [
    "roles/aiplatform.user",
    "roles/datastore.user",
    "roles/storage.objectAdmin",
    "roles/run.invoker",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ]
}

resource "google_project_iam_member" "agent_roles" {
  for_each = toset(local.agent_roles)
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.agent_sa.email}"
}

# ------------------------------------------------------------------------------
# Cloud Firestore (Native Mode Database)
# ------------------------------------------------------------------------------

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  delete_protection_state = "DELETE_PROTECTION_DISABLED"
  deletion_policy         = "ABANDON"

  depends_on = [google_project_service.enabled_services]
}

# ------------------------------------------------------------------------------
# Google Cloud Storage Bucket (Media & AI-Generated Imagery)
# ------------------------------------------------------------------------------

resource "google_storage_bucket" "media_bucket" {
  name                        = var.media_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "OPTIONS"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  depends_on = [google_project_service.enabled_services]
}

# Public read access so frontend chat bubbles and external users can view generated dishes
resource "google_storage_bucket_iam_member" "public_media_read" {
  bucket = google_storage_bucket.media_bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# ------------------------------------------------------------------------------
# Artifact Registry Repository (Container Storage)
# ------------------------------------------------------------------------------

resource "google_artifact_registry_repository" "frontend_repo" {
  provider      = google-beta
  location      = var.region
  repository_id = var.artifact_registry_repo_id
  description   = "Docker repository for YomTov Kitchen Concierge frontend images"
  format        = "DOCKER"

  depends_on = [google_project_service.enabled_services]
}

# ------------------------------------------------------------------------------
# Cloud Run Service (Web Chat Frontend)
# ------------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "frontend" {
  name     = var.frontend_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_sa.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo_id}/frontend:latest"

      ports {
        container_port = 8080
      }

      env {
        name  = "AGENT_ENGINE_RESOURCE_NAME"
        value = var.agent_engine_resource_name
      }
      env {
        name  = "PORT"
        value = "8080"
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1024Mi"
        }
      }
    }
  }

  depends_on = [
    google_project_service.enabled_services,
    google_project_iam_member.agent_roles
  ]
}

# Allow unauthenticated invocations for the public web chat interface
resource "google_cloud_run_v2_service_iam_member" "public_frontend" {
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ------------------------------------------------------------------------------
# Operational Scripts & Data Seeding (Local-Exec Triggers)
# ------------------------------------------------------------------------------

# Seeds Firestore with all 19 kosher recipes and menu items
resource "null_resource" "seed_firestore" {
  count = var.enable_seeding ? 1 : 0

  provisioner "local-exec" {
    command = <<-EOT
      python3 scripts/seed_firestore.py
      python3 scripts/seed_menu_recipes.py
    EOT
    environment = {
      GOOGLE_CLOUD_PROJECT = var.project_id
    }
  }

  depends_on = [google_firestore_database.default]
}

# Provisions the Vertex AI RAG corpus with authentic kosher culinary blog recipes
resource "null_resource" "provision_rag_corpus" {
  count = var.enable_seeding ? 1 : 0

  provisioner "local-exec" {
    command = "python3 scripts/create_rag_corpus.py"
    environment = {
      GOOGLE_CLOUD_PROJECT = var.project_id
      GOOGLE_CLOUD_REGION  = var.region
    }
  }

  depends_on = [google_project_service.enabled_services]
}

# ------------------------------------------------------------------------------
# Outputs & Verbatim CLI Command Cheatsheet
# ------------------------------------------------------------------------------

output "cloud_run_frontend_url" {
  description = "Public URL of the deployed Cloud Run chat frontend."
  value       = google_cloud_run_v2_service.frontend.uri
}

output "media_bucket_url" {
  description = "Public GCS URL for recipe media and generated food imagery."
  value       = "https://storage.googleapis.com/${google_storage_bucket.media_bucket.name}"
}

output "service_account_email" {
  description = "Email of the provisioned service account."
  value       = google_service_account.agent_sa.email
}

output "firestore_database_name" {
  description = "Name of the Firestore Native database."
  value       = google_firestore_database.default.name
}

output "cli_commands_cheatsheet" {
  description = "Exact CLI commands used to operate, test, build, and deploy the application."
  value = {
    auth_login           = "gcloud auth login && gcloud auth application-default login"
    set_project          = "gcloud config set project ${var.project_id}"
    seed_firestore       = "python3 scripts/seed_firestore.py && python3 scripts/seed_menu_recipes.py"
    build_rag_corpus     = "python3 scripts/create_rag_corpus.py"
    run_unit_tests       = "GOOGLE_GENAI_USE_VERTEXAI=true uv run pytest tests/unit/"
    run_local_playground = "agents-cli playground --host 0.0.0.0 --port 8000"
    run_local_frontend   = "cd frontend && AGENT_ENGINE_RESOURCE_NAME=\"${var.agent_engine_resource_name}\" PORT=8080 uv run python3 main.py"
    deploy_agent_engine  = "uv run agents-cli deploy --project ${var.project_id} --region ${var.region} --no-confirm-project"
    deploy_cloud_run     = "cd frontend && gcloud run deploy ${var.frontend_service_name} --source . --region ${var.region} --project ${var.project_id} --set-env-vars AGENT_ENGINE_RESOURCE_NAME=${var.agent_engine_resource_name} --quiet"
    record_demo_video    = "uv run --with playwright python3 scripts/record_demo.py"
  }
}
