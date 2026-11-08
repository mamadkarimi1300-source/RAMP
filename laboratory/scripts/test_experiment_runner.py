import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("run_experiments.py")
SPEC = importlib.util.spec_from_file_location("ramp_experiment_runner", SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class ExperimentRunnerTests(unittest.TestCase):
    def test_percentile_interpolates(self):
        self.assertEqual(RUNNER.percentile([0, 10, 20, 30, 40], 0.5), 20)
        self.assertEqual(RUNNER.percentile([0, 10, 20, 30, 40], 0.95), 38)

    def test_empty_percentile_is_none(self):
        self.assertIsNone(RUNNER.percentile([], 0.95))

    def test_summary_keeps_failed_runs_in_success_denominator(self):
        rows = RUNNER.summarize([
            {"scenario_id": "baseline", "mode": "direct", "success": True,
             "goodput_mbps": 8.0, "transfer_duration_ms": 100.0},
            {"scenario_id": "baseline", "mode": "direct", "success": True,
             "goodput_mbps": 12.0, "transfer_duration_ms": 80.0},
            {"scenario_id": "baseline", "mode": "direct", "success": False,
             "goodput_mbps": None, "transfer_duration_ms": None},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["runs"], 3)
        self.assertEqual(rows[0]["successes"], 2)
        self.assertEqual(rows[0]["failures"], 1)
        self.assertAlmostEqual(rows[0]["success_rate"], 2 / 3)
        self.assertEqual(rows[0]["goodput_mbps_median"], 10.0)

    def test_summary_groups_modes_separately(self):
        rows = RUNNER.summarize([
            {"scenario_id": "baseline", "mode": "direct", "success": True,
             "goodput_mbps": 10.0, "transfer_duration_ms": 10.0},
            {"scenario_id": "baseline", "mode": "ramp-fixed", "success": True,
             "goodput_mbps": 8.0, "transfer_duration_ms": 12.0},
        ])
        self.assertEqual({(x["scenario_id"], x["mode"]) for x in rows},
                         {("baseline", "direct"), ("baseline", "ramp-fixed")})


if __name__ == "__main__":
    unittest.main()
