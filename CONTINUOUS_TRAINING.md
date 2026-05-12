# Continuous Training & Model Drift

## Overview

Full R2O (Research to Operations) pipeline with automatic model retraining and evaluation.

## Promotion Gate Logic

4-point quality check (ALL must pass):
1. mAP improvement >= 1%
2. Precision >= 0.70
3. Recall >= 0.70
4. Absolute mAP >= 0.50

Result:
- PASS ALL → Production (auto-deployed)
- FAIL ANY → Staging (manual review)

## Data Flow

New Data → S3 → GitHub Actions → Train → Evaluate → Gate Decision

If PASS: Production v2 → Inference API loads → Baseline updated
If FAIL: Staging v2 → Manual review → Old model stays live

## Model Drift Prevention

- Daily retraining on new data
- Automatic evaluation every model
- Gate blocks bad models from production
- Feedback loop improves future models

## Quick Start

Local test:
```bash
python scripts/trigger_training.py
```

AWS deploy:
```bash
cd infra && terraform apply
```

MLflow server:
```bash
mlflow server --backend-store-uri sqlite:///mlflow.db
```

GitHub Actions (automatic):
Push to main → continuous-training.yml runs daily 2 AM UTC

## Components

- **src/train.py** - Fine-tune YOLOv8n, log to MLflow
- **src/evaluate.py** - Promotion gate logic
- **src/registry.py** - MLflow registry
- **scripts/trigger_training.py** - CT orchestration
- **.github/workflows/continuous-training.yml** - Scheduled pipeline
- **infra/s3.tf** - Training data, models, MLflow buckets
- **infra/stepfunctions.tf** - AWS Step Functions orchestration
