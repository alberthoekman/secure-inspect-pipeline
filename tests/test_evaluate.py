"""Unit tests for evaluate module — ModelGate promotion logic."""

import pytest
from src.evaluate import ModelGate, EvaluationResult


class TestModelGate:
    """Promotion gate tests."""

    def test_gate_all_checks_pass_production(self):
        """All gates pass → Production."""
        gate = ModelGate()
        new = {"mAP": 0.75, "precision": 0.85, "recall": 0.80}
        baseline = {"mAP": 0.50, "precision": 0.72, "recall": 0.68}

        result = gate.evaluate(new, baseline, model_version="v2.0")

        assert result.passed_gate is True
        assert result.promotion_stage == "Production"
        assert "passed all gates" in result.reason.lower()
        assert result.model_version == "v2.0"

    def test_fails_mAP_improvement_staging(self):
        """mAP improvement below threshold → Staging."""
        gate = ModelGate()
        new = {"mAP": 0.50, "precision": 0.85, "recall": 0.80}
        baseline = {"mAP": 0.50, "precision": 0.72, "recall": 0.68}

        result = gate.evaluate(new, baseline)

        assert result.passed_gate is False
        assert result.promotion_stage == "Staging"
        assert "mAP improvement" in result.reason

    def test_fails_precision_staging(self):
        """Precision below threshold → Staging."""
        gate = ModelGate()
        new = {"mAP": 0.75, "precision": 0.50, "recall": 0.80}
        baseline = {"mAP": 0.50, "precision": 0.72, "recall": 0.68}

        result = gate.evaluate(new, baseline)

        assert result.passed_gate is False
        assert result.promotion_stage == "Staging"
        assert "precision" in result.reason.lower()

    def test_fails_recall_staging(self):
        """Recall below threshold → Staging."""
        gate = ModelGate()
        new = {"mAP": 0.75, "precision": 0.85, "recall": 0.50}
        baseline = {"mAP": 0.50, "precision": 0.72, "recall": 0.68}

        result = gate.evaluate(new, baseline)

        assert result.passed_gate is False
        assert result.promotion_stage == "Staging"
        assert "recall" in result.reason.lower()

    def test_fails_absolute_mAP_staging(self):
        """Absolute mAP below threshold → Staging."""
        gate = ModelGate()
        new = {"mAP": 0.30, "precision": 0.85, "recall": 0.80}
        baseline = {"mAP": 0.50, "precision": 0.72, "recall": 0.68}

        result = gate.evaluate(new, baseline)

        assert result.passed_gate is False
        assert result.promotion_stage == "Staging"
        assert "mAP" in result.reason

    def test_no_baseline_with_good_metrics_passes(self):
        """No baseline provided — passes if absolute metrics are good."""
        gate = ModelGate()
        new = {"mAP": 0.75, "precision": 0.85, "recall": 0.80}

        result = gate.evaluate(new, model_version="v1.0")

        assert result.passed_gate is True
        assert result.promotion_stage == "Production"
        assert result.baseline_metrics == {"mAP": 0.0, "precision": 0.0, "recall": 0.0}

    def test_no_baseline_with_bad_metrics_fails(self):
        """No baseline and poor absolute metrics → Staging."""
        gate = ModelGate()
        new = {"mAP": 0.30, "precision": 0.50, "recall": 0.40}

        result = gate.evaluate(new)

        assert result.passed_gate is False
        assert result.promotion_stage == "Staging"

    def test_default_constructor_values(self):
        """Default gate thresholds match config spec."""
        gate = ModelGate()
        assert gate.min_mAP_improvement == 0.01
        assert gate.min_precision == 0.7
        assert gate.min_recall == 0.7
        assert gate.min_absolute_mAP == 0.5

    def test_custom_thresholds(self):
        """Custom gate thresholds are respected."""
        gate = ModelGate(
            min_mAP_improvement=0.05,
            min_precision=0.9,
            min_recall=0.9,
            min_absolute_mAP=0.8,
        )
        new = {"mAP": 0.85, "precision": 0.92, "recall": 0.91}
        baseline = {"mAP": 0.75, "precision": 0.80, "recall": 0.80}

        result = gate.evaluate(new, baseline)

        assert result.passed_gate is True
        assert result.promotion_stage == "Production"
        # mAP improvement 0.85 → (0.85-0.75)/0.75 = 13.3% > 5%
        assert result.improvements["mAP_pct"] == pytest.approx(13.333, rel=0.1)

    def test_evaluation_result_dataclass(self):
        """EvaluationResult has correct fields."""
        result = EvaluationResult(
            model_version="v1",
            metrics={"mAP": 0.5},
            baseline_metrics={"mAP": 0.4},
            improvements={"mAP_pct": 25.0},
            passed_gate=True,
            promotion_stage="Production",
            reason="Good enough",
        )

        assert result.model_version == "v1"
        assert result.passed_gate is True
        assert result.promotion_stage == "Production"
        assert result.reason == "Good enough"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
