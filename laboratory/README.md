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
| `deployments/docker/` | Local reproducible deployment instructions |

## Initial topology

The first target is a three-role topology:

1. **Client** — runs the existing SOCKS5 client and produces application traffic.
2. **Bridge** — runs the existing TLS bridge and connects to the destination.
3. **Destination** — a controlled HTTP/TCP endpoint whose response size and behavior are known.

A network-emulation hop is placed between Client and Bridge. The emulator must be on the actual packet path; applying `tc netem` to an unrelated interface does not constitute a valid experiment.

Monitoring observes all roles and the emulation hop. RAMP's own SQLite event databases remain process-local; laboratory run metadata and raw measurement samples are separate concerns.

## Current implementation status

This directory establishes the lab specification and experiment contracts. It is not yet a runnable Compose testbed. Container routing, certificate provisioning, traffic shaping, metric exporters and end-to-end orchestration must be implemented and validated in the next phase.

See:

- [Topology](topology.md)
- [Scenario matrix](scenarios/matrix.yaml)
- [Experiment contract](experiments/README.md)
- [Docker deployment plan](../deployments/docker/README.md)
