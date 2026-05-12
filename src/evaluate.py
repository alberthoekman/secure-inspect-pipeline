"""Model evaluation and promotion gate."""

import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of model evaluation."""

    model_version: str
    metrics: Dict[str, float]
    baseline_metrics: Dict[str, float]
    improvements: Dict[str, float]
    passed_gate: bool
    promotion_stage: str
    reason: str


class ModelGate:
    """Promotion gate for model deployment."""

    def __init__(
        self,
        min_mAP_improvement: float = 0.01,
        min_precision: float = 0.7,
        min_recall: float = 0.7,
        min_absolute_mAP: float = 0.5,
    ):
        """Initialize promotion gate."""
        self.min_mAP_improvement = min_mAP_improvement
        self.min_precision = min_precision
        self.min_recall = min_recall
        self.min_absolute_mAP = min_absolute_mAP

    def evaluate(
        self,
        new_metrics: Dict[str, float],
        baseline_metrics: Optional[Dict[str, float]] = None,
        model_version: str = "unknown",
    ) -> EvaluationResult:
        """Evaluate model and determine promotion stage."""
        if baseline_metrics is None:
            baseline_metrics = {"mAP": 0.0, "precision": 0.0, "recall": 0.0}

        improvements = self._calculate_improvements(new_metrics, baseline_metrics)

        checks = {
            "mAP_improvement": improvements.get("mAP_pct", 0)
            >= self.min_mAP_improvement * 100,
            "min_precision": new_metrics.get("precision", 0) >= self.min_precision,
            "min_recall": new_metrics.get("recall", 0) >= self.min_recall,
            "min_absolute_mAP": new_metrics.get("mAP", 0) >= self.min_absolute_mAP,
        }

        passed_gate = all(checks.values())
        promotion_stage = "Production" if passed_gate else "Staging"
        reason = self._generate_reason(checks, improvements)

        result = EvaluationResult(
            model_version=model_version,
            metrics=new_metrics,
            baseline_metrics=baseline_metrics,
            improvements=improvements,
            passed_gate=passed_gate,
            promotion_stage=promotion_stage,
            reason=reason,
        )

        logger.info(
            f"Model evaluation: {model_version}, Passed: {passed_gate}, Stage: {promotion_stage}"
        )
        return result

    def _calculate_improvements(
        self, new_metrics: Dict[str, float], baseline_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate metric improvements."""
        improvements = {}

        for metric in ["mAP", "precision", "recall"]:
            new_val = new_metrics.get(metric, 0)
            base_val = baseline_metrics.get(metric, 0)

            if base_val > 0:
                pct_change = (new_val - base_val) / base_val * 100
            else:
                pct_change = 100 if new_val > 0 else 0

            improvements[f"{metric}_pct"] = pct_change
            improvements[f"{metric}_abs"] = new_val - base_val

        return improvements

    def _generate_reason(
        self, checks: Dict[str, bool], improvements: Dict[str, float]
    ) -> str:
        """Generate promotion reason/rejection reason."""
        failed = [k for k, v in checks.items() if not v]

        if not failed:
            mAP_improvement = improvements.get("mAP_pct", 0)
            return f"Model passed all gates. mAP improved by {mAP_improvement:.2f}%"

        reasons = []
        for check in failed:
            if check == "mAP_improvement":
                reasons.append(
                    f"mAP improvement {improvements.get('mAP_pct', 0):.2f}% < {self.min_mAP_improvement * 100:.1f}%"
                )
            elif check == "min_precision":
                reasons.append(f"Precision below {self.min_precision}")
            elif check == "min_recall":
                reasons.append(f"Recall below {self.min_recall}")
            elif check == "min_absolute_mAP":
                reasons.append(f"Absolute mAP below {self.min_absolute_mAP}")

        return "; ".join(reasons)
