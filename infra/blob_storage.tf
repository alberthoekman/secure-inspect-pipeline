# Azure Blob Storage — replaces AWS S3 buckets
# Three containers: training data, model artifacts, MLflow experiment tracking
#
# Usage: include this alongside main.tf in your Terraform workspace.
# The storage account name must be globally unique (3–24 alphanumeric chars).
# A random suffix is appended to avoid collisions.

variable "storage_account_name" {
  description = "Base name for the storage account (a random hex suffix is appended)"
  type        = string
  default     = "teststorageahmay"
}

variable "resource_group_name" {
  description = "Resource group name — reuse from main.tf or set here"
  type        = string
  default     = "Test"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westeurope"
}

resource "random_id" "storage_suffix" {
  byte_length = 4
}

# Storage account — holds blobs for training data, models, and experiment tracking
resource "azurerm_storage_account" "training" {
  name                     = "${var.storage_account_name}${random_id.storage_suffix.hex}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Allow blob public access to remain disabled by default
  allow_nested_items_to_be_public = false

  tags = {
    Name    = "SecureInspect Training"
    Purpose = "ML Pipeline Storage"
  }
}

# Training data container — raw images and annotations
resource "azurerm_storage_container" "training_data" {
  name                  = "training-data"
  storage_account_name  = azurerm_storage_account.training.name
  container_access_type = "private"
}

# Model artifacts container — trained model weights and metadata
resource "azurerm_storage_container" "model_artifacts" {
  name                  = "model-artifacts"
  storage_account_name  = azurerm_storage_account.training.name
  container_access_type = "private"
}

# MLflow container — experiment tracking data (artifacts, runs)
resource "azurerm_storage_container" "mlflow" {
  name                  = "mlflow"
  storage_account_name  = azurerm_storage_account.training.name
  container_access_type = "private"
}

# --- RBAC: grant the existing managed identity access to blob storage ---
# Assumes azurerm_user_assigned_identity.main exists (from main.tf).
# These let the container group / Logic App read and write blobs.

data "azurerm_user_assigned_identity" "pipeline" {
  name                = "uai-az2003"
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = azurerm_storage_account.training.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.pipeline.principal_id
}

# Outputs
output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.training.name
}

output "primary_blob_endpoint" {
  description = "Blob service primary endpoint"
  value       = azurerm_storage_account.training.primary_blob_endpoint
}

output "training_data_container" {
  description = "Training data container name"
  value       = azurerm_storage_container.training_data.name
}

output "model_artifacts_container" {
  description = "Model artifacts container name"
  value       = azurerm_storage_container.model_artifacts.name
}

output "mlflow_container" {
  description = "MLflow artifact container name"
  value       = azurerm_storage_container.mlflow.name
}
