variable "aws_region" {
  type    = string
  default = "us-east-1"
}

resource "aws_s3_bucket" "training_data" {
  bucket = "secure-inspect-training-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "Training Data"
    Purpose = "Model Training"
  }
}

resource "aws_s3_bucket" "model_artifacts" {
  bucket = "secure-inspect-models-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "Model Artifacts"
    Purpose = "ML Models"
  }
}

resource "aws_s3_bucket" "mlflow" {
  bucket = "secure-inspect-mlflow-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name    = "MLflow Artifacts"
    Purpose = "Experiment Tracking"
  }
}

data "aws_caller_identity" "current" {}

output "training_bucket" {
  value = aws_s3_bucket.training_data.id
}

output "models_bucket" {
  value = aws_s3_bucket.model_artifacts.id
}

output "mlflow_bucket" {
  value = aws_s3_bucket.mlflow.id
}
