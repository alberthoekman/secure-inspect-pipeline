# Secure Inspect Pipeline

ML inspection system with continuous training and automatic model promotion.

## Project Structure

```
secure-inspect-pipeline/
├── src/
│   ├── app.py           # FastAPI application
│   ├── model.py         # YOLOv8 inference wrapper
│   ├── validation.py    # Image validation (format, size, resolution)
│   └── monitoring.py    # Structured logging & metrics
├── tests/
│   └── test_api.py      # Pytest + FastAPI TestClient
├── infra/
│   ├── main.tf          # Terraform for Azure Container Instance
│   └── terraform.tfvars.example
├── .github/workflows/
│   └── mlops-pipeline.yml  # GitHub Actions CI/CD
├── Dockerfile           # Multi-stage Docker build
├── requirements.txt     # Python dependencies
└── README.md
```

## Quick Start

### Local Development

```bash
# Clone repo
git clone <repo-url>
cd secure-inspect-pipeline

# Create venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start server
python -m uvicorn src.app:app --reload

# API available at http://localhost:8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# API info
curl http://localhost:8000/info

# Single image inspection
curl -F "file=@sample.jpg" http://localhost:8000/inspect

# Batch inspection (max 10 files)
curl -F "file=@img1.jpg" -F "file=@img2.jpg" http://localhost:8000/batch
```

## Continuous Training

This project includes a continuous training pipeline that keeps the inspection model fresh and safe. When new data is available, the pipeline retrains the model, evaluates it, and decides whether the new version should go to production or remain in staging for review.

- New data lands in S3 and triggers model retraining
- Each candidate model is evaluated against a promotion gate
- Passing models are promoted to production automatically
- Failing models are held for manual review
- This helps prevent model drift and avoids deploying bad updates

### Promotion gate

The pipeline checks:

- mAP improvement >= 1%
- Precision >= 0.70
- Recall >= 0.70
- Absolute mAP >= 0.50

Result:
- PASS ALL → Production
- FAIL ANY → Staging for review

### How it runs

- Local test: `python scripts/trigger_training.py`
- AWS deploy: `cd infra && terraform apply`
- GitHub Actions can run the pipeline on a schedule or in CI

## Docker

### Build Image

```bash
docker build -t secure-inspect:latest .
```

### Run Container

```bash
docker run -p 8000:8000 \
  --name inspect-pipeline \
  secure-inspect:latest
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Azure Deployment

### Prerequisites

```bash
# Install Terraform
brew install terraform

# Azure CLI
az login
az account set --subscription <subscription-id>
```

### Deploy Infrastructure

```bash
cd infra

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="image_pull_username=<registry-user>" \
  -var="image_pull_password=<registry-pass>"

# Apply
terraform apply
```

### Outputs

```bash
terraform output container_instance_url
# http://secure-inspect-pipeline.eastus.azurecontainer.io:8000
```

## API Reference

### POST /inspect

Single image inspection.

**Request:**
```bash
curl -F "file=@image.jpg" http://localhost:8000/inspect
```

**Response:**
```json
{
  "request_id": "uuid",
  "status": "success",
  "image_metadata": {
    "width": 1920,
    "height": 1080,
    "format": "JPEG",
    "file_size_bytes": 245392
  },
  "detections": [
    {
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.95,
      "box": {
        "x_min": 100.5,
        "y_min": 200.3,
        "x_max": 500.2,
        "y_max": 800.1
      },
      "box_area": 280000.0
    }
  ],
  "summary": {
    "total_detections": 3,
    "avg_confidence": 0.92
  },
  "metrics": {
    "inference_time_ms": 145.3,
    "total_request_time_ms": 156.7
  }
}
```

### POST /batch

Batch inspection (max 10 files).

**Request:**
```bash
curl -F "file=@img1.jpg" -F "file=@img2.jpg" http://localhost:8000/batch
```

**Response:**
```json
{
  "batch_id": "uuid",
  "total_files": 2,
  "successful": 2,
  "failed": 0,
  "results": [...]
}
```

### GET /health

Health check.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### GET /info

API info and validation rules.

**Response:**
```json
{
  "service": "Secure Inspect Pipeline",
  "version": "1.0.0",
  "model": {
    "model_name": "yolov8n.pt",
    "framework": "ultralytics/YOLOv8",
    "confidence_threshold": 0.5,
    "task": "object-detection"
  },
  "validation": {
    "min_width": 64,
    "min_height": 64,
    "max_file_size_mb": 10,
    "allowed_formats": ["PNG", "JPEG", "JPG", "BMP", "TIFF"]
  }
}
```

## Continuous Training

Automatic model retraining with evaluation gate. See CONTINUOUS_TRAINING.md for full documentation.

## License

MIT
