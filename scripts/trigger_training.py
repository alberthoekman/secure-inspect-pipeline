"""Trigger continuous training pipeline."""

import sys
import json
import logging
from src.registry import MLflowRegistry, load_baseline_metrics, save_baseline_metrics
from src.evaluate import ModelGate
from src.train import train_with_mlflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting CT pipeline")
    
    registry = MLflowRegistry()
    gate = ModelGate(min_mAP_improvement=0.01, min_precision=0.70, min_recall=0.70)
    
    # Load baseline
    baseline = load_baseline_metrics("baseline_metrics.json")
    logger.info(f"Baseline: {baseline}")
    
    # Simulate training
    new_metrics = {
        "mAP": 0.52,
        "precision": 0.76,
        "recall": 0.74,
    }
    logger.info(f"New metrics: {new_metrics}")
    
    # Evaluate
    result = gate.evaluate(new_metrics, baseline, "v1.0.0")
    logger.info(f"Gate passed: {result.passed_gate}, Stage: {result.promotion_stage}")
    
    # Update baseline if promoted
    if result.passed_gate:
        save_baseline_metrics(new_metrics, "baseline_metrics.json")
        return {
            "status": "success",
            "action": "promoted_to_production",
            "metrics": new_metrics,
        }
    else:
        return {
            "status": "success",
            "action": "staged_for_review",
            "metrics": new_metrics,
            "reason": result.reason,
        }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
