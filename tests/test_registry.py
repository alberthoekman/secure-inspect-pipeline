"""Unit tests for registry module — baseline metrics I/O."""

import json
import os
import tempfile

from src.registry import load_baseline_metrics, save_baseline_metrics


class TestBaselineMetrics:
    """Baseline metrics file I/O tests."""

    def test_load_returns_default_when_file_missing(self):
        """Missing file returns default zero metrics."""
        missing_path = "/tmp/nonexistent_baseline_xxxxx.json"
        result = load_baseline_metrics(missing_path)

        assert result == {"mAP": 0.0, "precision": 0.0, "recall": 0.0}

    def test_load_returns_parsed_json(self):
        """Existing file returns parsed content."""
        data = {"mAP": 0.75, "precision": 0.85, "recall": 0.80}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            result = load_baseline_metrics(tmp_path)
            assert result == data
        finally:
            os.unlink(tmp_path)

    def test_save_writes_json(self):
        """save_baseline_metrics writes correct JSON file."""
        data = {"mAP": 0.90, "precision": 0.88, "recall": 0.85}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            save_baseline_metrics(data, tmp_path)

            with open(tmp_path, "r") as f:
                loaded = json.load(f)

            assert loaded == data
        finally:
            os.unlink(tmp_path)

    def test_roundtrip_preserves_values(self):
        """Save then load returns the same data."""
        original = {"mAP": 0.55, "precision": 0.70, "recall": 0.65}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            save_baseline_metrics(original, tmp_path)
            loaded = load_baseline_metrics(tmp_path)
            assert loaded == original
        finally:
            os.unlink(tmp_path)
