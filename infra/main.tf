terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

data "azurerm_role_definition" "acr_pull" {
  name  = "AcrPull"
  scope = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
}

# Variables
variable "resource_group_name" {
  description = "Name of resource group"
  type        = string
  default     = "Test"  # exercise uses RG1
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westeurope"  # your region, not Central US
}

variable "container_image" {
  description = "Docker image URI"
  type        = string
  default     = "secureinspect.azurecr.io/inspect-pipeline:latest"
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8000
}

variable "container_registry_name" {
  description = "Container Registry Name"
  type        = string
  default     = "acraz2003AHMay"
}

variable "service_bus_name" {
  description = "Service Bus Name"
  type        = string
  default     = "sb-az2003-AH"
}

variable "managed_identity_name" {
  description = "Managed Identity Name"
  type        = string
  default     = "uai-az2003"
}

variable "vnet_name" {
  description = "VNET Name"
  type        = string
  default     = "VNET1"
}

variable "cpu_cores" {
  description = "CPU cores"
  type        = string
  default     = "1.0"
}

variable "memory_gb" {
  description = "Memory in GB"
  type        = string
  default     = "2.0"
}

variable "image_pull_username" {
  description = "Image registry username"
  type        = string
  sensitive   = true
}

variable "image_pull_password" {
  description = "Image registry password"
  type        = string
  sensitive   = true
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = "Production"
    Project     = "SecureInspect"
    ManagedBy   = "Terraform"
  }
}

# Container Registry
resource "azurerm_container_registry" "main" {
  name                = var.container_registry_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Premium"  # Premium required for private endpoints
  admin_enabled       = true

  # Disable public access so only the private endpoint is used
  public_network_access_enabled = false

  tags = {
    Environment = "Production"
    Project     = "SecureInspect"
  }
}

# Virtual Network and Subnets
resource "azurerm_virtual_network" "main" {
  name                = var.vnet_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]
}

# FIX: original had both subnets on 10.0.0.0 — PESubnet gets /24, ACASubnet gets a non-overlapping /23
resource "azurerm_subnet" "pe_subnet" {
  name                 = "PESubnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.0.0/24"]

  # Private endpoint network policies must be disabled on the subnet
  private_endpoint_network_policies_enabled = false
}

resource "azurerm_subnet" "aca_subnet" {
  name                 = "ACASubnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/23"]  # FIX: was 10.0.0.0/23 which overlapped PESubnet
}

# User-assigned managed identity
resource "azurerm_user_assigned_identity" "main" {
  name                = var.managed_identity_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# AcrPull role assignment for the managed identity — principle of least privilege
resource "random_uuid" "acr_role" {}

resource "azurerm_role_assignment" "acr_pull_for_identity" {
  scope              = azurerm_container_registry.main.id
  role_definition_id = data.azurerm_role_definition.acr_pull.id
  principal_id       = azurerm_user_assigned_identity.main.principal_id
  name               = random_uuid.acr_role.result
}

# --- PRIVATE ENDPOINT FOR CONTAINER REGISTRY (new — the core exercise task) ---

resource "azurerm_private_dns_zone" "acr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "acr" {
  name                  = "acr-dns-vnet-link"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.acr.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
}

resource "azurerm_private_endpoint" "acr" {
  name                = "pe-acr-az2003"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.pe_subnet.id

  private_service_connection {
    name                           = "acr-private-connection"
    private_connection_resource_id = azurerm_container_registry.main.id
    subresource_names              = ["registry"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "acr-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.acr.id]
  }

  tags = {
    Environment = "Production"
    Project     = "SecureInspect"
  }
}

# --- END PRIVATE ENDPOINT ---

# Service Bus namespace
# FIX: capacity is only valid for Premium SKU; removed from Standard
resource "azurerm_servicebus_namespace" "main" {
  name                = "${var.resource_group_name}-sb-namespace"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"

  tags = {
    Environment = "Production"
    Project     = "SecureInspect"
  }
}

resource "azurerm_servicebus_queue" "main" {
  name         = "inspect-queue"
  namespace_id = azurerm_servicebus_namespace.main.id  # preferred over deprecated namespace_name

  enable_partitioning   = false
  max_size_in_megabytes = 1024
}

# Azure Container Instance
resource "azurerm_container_group" "main" {
  name                = "secure-inspect-pipeline"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  ip_address_type     = "Public"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  container {
    name   = "inspect-pipeline"
    image  = var.container_image
    cpu    = var.cpu_cores
    memory = var.memory_gb

    ports {
      port     = var.container_port
      protocol = "TCP"
    }

    liveness_probe {
      http_get {
        path   = "/health"
        port   = var.container_port
        scheme = "HTTP"
      }
      initial_delay_seconds = 60
      period_seconds        = 20
      failure_threshold     = 3
      timeout_seconds       = 10
    }

    readiness_probe {
      http_get {
        path   = "/health"
        port   = var.container_port
        scheme = "HTTP"
      }
      initial_delay_seconds = 30
      period_seconds        = 10
      failure_threshold     = 3
      timeout_seconds       = 5
    }

    environment_variables = {
      LOG_LEVEL = "INFO"
    }
  }

  image_registry_credential {
    username = var.image_pull_username
    password = var.image_pull_password
    server   = "${azurerm_container_registry.main.name}.azurecr.io"
  }

  restart_policy = "Always"

  tags = {
    Environment = "Production"
    Project     = "SecureInspect"
    ManagedBy   = "Terraform"
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "secure-inspect-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = "Production"
    Project     = "SecureInspect"
  }
}

# Outputs
output "container_registry_name" {
  value = azurerm_container_registry.main.name
}

output "container_registry_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "container_instance_fqdn" {
  value = azurerm_container_group.main.fqdn
}

output "container_instance_ip" {
  value = azurerm_container_group.main.ip_address
}

output "container_instance_url" {
  value = "http://${azurerm_container_group.main.fqdn}:${var.container_port}"
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.main.workspace_id
}

output "private_endpoint_id" {
  description = "Private endpoint for Container Registry"
  value       = azurerm_private_endpoint.acr.id
}