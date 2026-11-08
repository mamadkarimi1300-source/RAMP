# RAMP Laboratory

The laboratory is an additive evaluation layer around the existing RAMP client, bridge, protocol and storage modules. It does not replace the data plane and must not introduce test-only behavior into production request handling.

## Goals

- Run the real RAMP client and bridge against controlled destinations.
- Apply reproducible network conditions between the client and bridge.
- Generate repeatable workloads and record the exact experiment configuration.
- Collect raw observations separately from derived metrics.
- Compare direct networking, fixed-path RAMP and (when implemented) adaptive RAMP.
- Produce machine-readable results and human-readable reports.

## Boundaries

| Area | Responsibility |
|---|---|
| `client/`, `server/`, `protocol/` | Production RAMP data/control path |
| `storage/` | Process-local RAMP event persistence |
| `laboratory/topology/` | Testbed topology and network boundaries |
| `laboratory/scenarios/` | Versioned network-condition profiles |
| `laboratory/workloads/` | Traffic generators and destination fixtures |
| `laboratory/experiments/` | Run definitions, IDs, repetitions and raw result contracts |
| `laboratory/monitoring/` | Host/container/network metric collection |
| `laboratory/reports/` | Analysis outputs and report templates |
| `deployments/docker/` | Local reproducible deployment, images and topology |

## Initial topology

The first Docker topology has three functional roles and an explicit transit router:

1. **Client** — existing SOCKS5 client and curl workload on `172.28.10.10`.
2. **Network Emulator** — router at `172.28.10.2` and `172.28.20.2`, shaping both egress directions.
3. **Bridge and Destination** — RAMP bridge at `172.28.20.10` and controlled HTTP destination at `172.28.20.11`.

The client and bridge are on separate Docker networks. Specific routes send client-to-bridge traffic and its return path through the emulator. The destination remains on the bridge-side network.

## Current implementation status

- Laboratory architecture, topology specification, scenario matrix and experiment contract: added.
- Dockerfiles, Compose topology, local certificate helper and Linux traffic-emulation router: added as an initial implementation scaffold.
- Repeatable Docker smoke-test script: added; checks Compose validation, image builds, direct and SOCKS5 requests, transit-router packet capture and NetEm qdisc installation.
- GitHub Actions Docker integration workflow: **passed** on GitHub-hosted Ubuntu at commit `2cbcc003af44b30f39833040cc58fac6ff55475d`; image builds, direct/SOCKS5 traffic, forward and return packet captures, NetEm qdisc installation and a two-scenario experiment all succeeded. Local Docker Desktop/WSL2 validation is still pending.
- Controlled HTTP workload destination with configurable payload size: implemented.
- Machine-readable scenario matrix in `scenarios/matrix.json`: implemented alongside the human-readable YAML matrix.
- Standard-library experiment runner with direct/RAMP modes, repetitions, warm-ups, raw JSONL, manifests, ICMP RTT/packet-loss probes, certificate-verified bridge TLS handshake probes, qdisc/container snapshots and statistical report: implemented.
- Python unit tests and CI integration for runner/statistics: added; first CI result remains pending.

See:

- [Topology](topology.md)
- [Scenario matrix (human-readable)](scenarios/matrix.yaml)
- [Scenario matrix (machine-readable)](scenarios/matrix.json)
- [Experiment runner](scripts/run_experiments.py)
- [Experiment contract](experiments/README.md)
- [Docker deployment](../deployments/docker/README.md)
