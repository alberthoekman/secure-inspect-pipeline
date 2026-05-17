# Terraform configuration for Secure Inspect Pipeline on Azure

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Variables
variable "resource_group_name" {
  description = "Name of resource group"
  type        = string
  default     = "Test"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westeurope"
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

# Container Registry (for storing images)
resource "azurerm_container_registry" "main" {
  name                = "secureinspectacr${replace(var.location, " ", "")}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Premium"
  admin_enabled       = true

  tags = {
    Environment = "Production"
    Project     = "SecureInspect"
  }
}

# Azure Container Instance
resource "azurerm_container_group" "main" {
  name                = "secure-inspect-pipeline"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  ip_address_type     = "Public"

  container {
    name   = "inspect-pipeline"
    image  = var.container_image
    cpu    = var.cpu_cores
    memory = var.memory_gb

    ports {
      port     = var.container_port
      protocol = "TCP"
    }

    # Liveness probe
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

    # Readiness probe
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

# Azure Log Analytics Workspace
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
  description = "Container Registry name"
  value       = azurerm_container_registry.main.name
}

output "container_registry_login_server" {
  description = "Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "container_instance_fqdn" {
  description = "Container Instance FQDN"
  value       = azurerm_container_group.main.fqdn
}

output "container_instance_ip" {
  description = "Container Instance public IP"
  value       = azurerm_container_group.main.ip_address
}

output "container_instance_url" {
  description = "Container Instance API URL"
  value       = "http://${azurerm_container_group.main.fqdn}:${var.container_port}"
}

output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.main.workspace_id
}
