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
- GitHub Actions Docker integration workflow: added; its first run and local Docker Desktop/WSL2 execution must pass before the testbed is considered runtime-validated.
- Real benchmark execution and measurement/report pipeline: **not yet implemented or validated**.
- Metric collector, experiment runner and report generator: not yet implemented.

See:

- [Topology](topology.md)
- [Scenario matrix](scenarios/matrix.yaml)
- [Experiment contract](experiments/README.md)
- [Docker deployment](../deployments/docker/README.md)
