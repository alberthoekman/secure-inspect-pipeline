# Azure Logic App (Standard) — replaces AWS Step Functions state machine
#
# Continuous training pipeline orchestration:
#   CheckNewData → TrainModel → EvaluateModel → DecidePromotion
#                                                   ├→ PromoteProduction
#                                                   └→ StageForReview
#
# The Logic App runs on a recurrence schedule and uses a managed identity
# (uai-az2003 from main.tf) to authenticate against blob storage.

variable "orchestrator_resource_group" {
  description = "Resource group name"
  type        = string
  default     = "Test"
}

variable "orchestrator_location" {
  description = "Azure region"
  type        = string
  default     = "westeurope"
}

variable "storage_account_name" {
  description = "Storage account name for the Logic App (not the training blobs — the built-in host storage)"
  type        = string
  default     = "secureinspectlogicapp"
}

# Resolve the existing managed identity created in main.tf
data "azurerm_user_assigned_identity" "orchestrator" {
  name                = "uai-az2003"
  resource_group_name = var.orchestrator_resource_group
}

# Managed identities enabled on the Logic App so it can use RBAC to access blob storage
resource "azurerm_logic_app_standard" "ct_pipeline" {
  name                       = "secure-inspect-ct-pipeline"
  resource_group_name        = var.orchestrator_resource_group
  location                   = var.orchestrator_location
  app_service_plan_id        = azurerm_service_plan.orchestrator.id
  storage_account_name       = azurerm_storage_account.orchestrator.name
  storage_account_access_key = azurerm_storage_account.orchestrator.primary_access_key
  storage_account_share_name = "ct-pipeline-share"

  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.orchestrator.id]
  }

  site_config {
    always_on       = false
    use_32_bit_worker_process = false
    app_scale_limit = 1
  }

  tags = {
    Name    = "Continuous Training Pipeline"
    Purpose = "ML Model Orchestration"
  }
}

# Consumption / Standard plan for the Logic App
resource "azurerm_service_plan" "orchestrator" {
  name                = "asp-secure-inspect-ct"
  resource_group_name = var.orchestrator_resource_group
  location            = var.orchestrator_location
  os_type             = "Linux"
  sku_name            = "WS1"  # Standard workflow service plan — stateful execution
}

# Dedicated storage account for the Logic App runtime (separate from training data blobs)
resource "random_id" "orchestrator_storage_suffix" {
  byte_length = 4
}

resource "azurerm_storage_account" "orchestrator" {
  name                     = "${var.storage_account_name}${random_id.orchestrator_storage_suffix.hex}"
  resource_group_name      = var.orchestrator_resource_group
  location                 = var.orchestrator_location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    Name    = "LogicApp Host Storage"
    Purpose = "CT Pipeline Orchestrator"
  }
}

# Workflow definition — maps the Step Functions state machine to Logic App actions
resource "azurerm_resource_group_template_deployment" "ct_workflow" {
  name                = "ct-pipeline-workflow-deployment"
  resource_group_name = var.orchestrator_resource_group
  deployment_mode     = "Incremental"

  template_content = jsonencode({
    "$schema" = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
    contentVersion = "1.0.0.0"
    resources = [
      {
        type      = "Microsoft.Logic/workflows"
        apiVersion = "2017-07-01"
        name      = "secure-inspect-ct-pipeline"
        location  = var.orchestrator_location
        # Properties omitted here because the workflow JSON is managed via
        # azurerm_logic_app_standard.app_settings[\"WORKFLOWS_JSON\"] or
        # portal/CLI deployment.
        # See the companion file logicapp-workflow.json for the actual definition.
      }
    ]
  })
}

# Outputs
output "logic_app_name" {
  description = "Logic App name"
  value       = azurerm_logic_app_standard.ct_pipeline.name
}

output "logic_app_default_hostname" {
  description = "Logic App default hostname (base URL for callback/management endpoints)"
  value       = azurerm_logic_app_standard.ct_pipeline.default_hostname
}
