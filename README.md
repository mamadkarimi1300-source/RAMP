# RAMP
## Resilient Adaptive Multipath Proxy

RAMP is an experimental Go-based resilient access network architecture. It is designed around independently deployable client and server programs, pluggable transports, multiple bridges, path measurement, session lifecycle management, and bounded recovery.

> Status: architecture baseline / early development. This repository does not yet claim production readiness or guaranteed censorship circumvention.

## Repository layout

- `client/`: user-side application, SOCKS5 ingress, access selection, session and recovery components.
- `server/`: bridge listener, authenticated tunnel endpoint, egress connector and server lifecycle.
- `protocol/`: versioned wire messages and shared protocol contracts.
- `docs/`: architecture, data flow, threat model, test plan and roadmap.
- `deployments/`: example service and container deployment assets.

Client and server are separate Go modules. The root `go.work` file ties the local modules together for development.

## Design goals

1. Keep the data plane separate from the control plane.
2. Keep bridge selection separate from transport selection.
3. Measure availability, RTT, throughput and failure history instead of selecting on a single metric.
4. Make transport adapters replaceable behind a small interface.
5. Track session state explicitly and distinguish reconnect from true transfer resumption.
6. Authenticate peers and protect configuration; never invent cryptography.
7. Keep telemetry minimal and avoid collecting destination browsing history.

## Initial implementation scope

The first baseline focuses on clean module boundaries, a client/server process split, protocol versioning, transport interfaces, health and recovery contracts, and buildable tests. TCP/TLS and QUIC adapters, full SOCKS5 forwarding, discovery, and resumable application transfers are staged features and must be marked complete only after integration tests demonstrate them.

## Build

Use Go 1.23 or newer.

```sh
go work sync
go test ./...
```

Run commands inside the relevant module if your Go installation does not support workspace mode:

```sh
cd protocol && go test ./...
cd client && go test ./...
cd server && go test ./...
```

## Security and operational limitations

- QUIC requires UDP reachability; it is not a fallback when UDP is unavailable.
- TLS does not by itself guarantee resistance to traffic classification or blocking.
- A new bridge cannot transparently continue an arbitrary existing TCP connection. Only application protocols designed for resumption can safely resume transfers.
- Do not expose an unauthenticated open proxy.
- Use established, reviewed cryptographic and pluggable-transport implementations.

See [docs/architecture.md](docs/architecture.md), [docs/threat-model.md](docs/threat-model.md), and [docs/roadmap.md](docs/roadmap.md).
