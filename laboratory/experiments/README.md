# Experiment Contract

Every run must be independently identifiable and reproducible. A result without its scenario, software revision and workload configuration is not an acceptable benchmark record.

## Required run metadata

- `experiment_id`: unique ID for one execution.
- `scenario_id`: stable ID from `scenarios/matrix.yaml`.
- `git_commit`: exact RAMP revision under test.
- `started_at_utc` and `finished_at_utc`.
- Host and runtime details: OS, kernel, Docker/Compose version, CPU and memory.
- Topology revision and network profile actually applied.
- Workload: destination, protocol, payload size, concurrency and duration.
- Mode: `direct`, `ramp-fixed` or `ramp-adaptive`.
- Repetition index and warm-up/measurement windows.

## Raw observations

Store timestamped samples where available. Preserve raw observations; do not keep only averages.

| Metric | Unit | Source / method |
|---|---|---|
| RTT | ms | Explicit probe with documented endpoints |
| Throughput | bit/s | Bytes transferred divided by measured interval |
| Goodput | bit/s | Application payload bytes divided by interval |
| Packet loss | percent | Emulator counters or packet-level observation |
| Jitter | ms | Variation of explicitly defined RTT/one-way samples |
| Connect duration | ms | Client-side monotonic timer |
| TLS handshake duration | ms | Client-side monotonic timer around handshake |
| Transfer duration | ms | Workload timer |
| Success / failure | count and ratio | Workload result |
| CPU / memory | percent / bytes | Container or host metrics |
| Active sessions | count | RAMP runtime instrumentation or process metrics |
| Recovery duration | ms | Time from injected fault to the defined recovery condition |

Every metric must identify its measurement point, sampling interval and calculation. Do not treat dial duration as end-to-end RTT. Do not infer throughput from a final byte counter without a valid time interval.

## RAMP-specific decision telemetry

When adaptive behavior is implemented, record:

- measured candidate/path values and measurement timestamp;
- selector input and selected candidate;
- selection reason and policy/config revision;
- recovery state transitions, retry count and backoff;
- whether the decision affected a new session or an existing one.

Never claim transparent migration of an arbitrary active TCP stream. A bridge failover test should distinguish new-session failover from application-level resumable transfer.

## Comparison and statistics

For each scenario and mode, report:

- number of valid runs and excluded runs with reasons;
- median, mean, standard deviation and p95 where meaningful;
- success rate and failure categories;
- throughput/goodput and latency distributions;
- CPU and memory overhead;
- relative change against the direct baseline.

Keep repetitions and workload constant across modes. Randomize or rotate execution order where practical to reduce time/order bias.

## Output layout

The planned output layout is:

```text
laboratory/results/
  <date>/
    <experiment-id>/
      manifest.json
      raw/
      summary.json
      report.md
```

Generated results are local artifacts and must not be committed by default. If a sanitized benchmark is published, include the manifest and exact revision.
