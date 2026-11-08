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

    def test_summary_computes_ramp_delta_against_direct(self):
        rows = RUNNER.summarize([
            {"scenario_id": "latency-100ms", "mode": "direct", "success": True,
             "goodput_mbps": 10.0, "transfer_duration_ms": 100.0},
            {"scenario_id": "latency-100ms", "mode": "ramp-fixed", "success": True,
             "goodput_mbps": 8.0, "transfer_duration_ms": 125.0},
        ])
        ramp = next(x for x in rows if x["mode"] == "ramp-fixed")
        self.assertAlmostEqual(ramp["goodput_change_vs_direct_percent"], -20.0)
        self.assertAlmostEqual(ramp["transfer_duration_change_vs_direct_percent"], 25.0)

    def test_parse_ping_output_extracts_rtt_and_loss(self):
        output = (
            "5 packets transmitted, 4 received, 20% packet loss, time 801ms\\n"
            "rtt min/avg/max/mdev = 10.000/20.000/30.000/5.000 ms\\n"
        )
        parsed = RUNNER.parse_ping_output(output)
        self.assertEqual(parsed["loss_percent"], 20.0)
        self.assertEqual(parsed["min_ms"], 10.0)
        self.assertEqual(parsed["avg_ms"], 20.0)
        self.assertEqual(parsed["max_ms"], 30.0)
        self.assertEqual(parsed["mdev_ms"], 5.0)

    def test_parse_tls_probe_separates_tcp_and_tls_time(self):
        parsed = RUNNER.parse_tls_probe("0.200000,0.404000")
        self.assertAlmostEqual(parsed["tcp_connect_ms"], 200.0)
        self.assertAlmostEqual(parsed["tls_handshake_ms"], 204.0)

    def test_parse_tls_probe_rejects_missing_timings(self):
        parsed = RUNNER.parse_tls_probe("0.200000")
        self.assertIsNone(parsed["tcp_connect_ms"])
        self.assertIsNone(parsed["tls_handshake_ms"])


if __name__ == "__main__":
    unittest.main()
