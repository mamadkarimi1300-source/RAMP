# RAMP
## Resilient Adaptive Multipath Proxy

RAMP is an experimental Go-based resilient access network architecture. It separates the user-side client from the remote bridge/egress server and provides explicit boundaries for transport selection, bridge selection, measurement, sessions and recovery.

> Status: early development baseline. This repository does not claim production readiness or guaranteed censorship circumvention.

## Repository layout

- `client/`: independent user-side Go module with SOCKS5 CONNECT ingress, TLS tunnel dialer, access selection, measurement types, session lifecycle, recovery primitives and a local SQLite event log.
- `server/`: independent server-side Go module with TLS bridge, token validation, TCP egress connector, health registry and a local SQLite event log.
- `protocol/`: shared, versioned wire protocol module.
- `storage/`: shared event contract, bounded asynchronous logger and SQLite repository. Client and server each own a separate database file.
- `docs/`: architecture, threat model, testing, storage and roadmap.
- `deployments/`: deployment guidance and secret-handling notes.

The root `go.work` file joins the four modules for local development. Client and server remain independently buildable and deployable; the storage module is a shared library, not a network service.

## Implemented baseline

- SOCKS5 CONNECT ingress on the client.
- TLS 1.3 client-to-bridge tunnel with certificate and server-name verification.
- Shared-token authentication inside TLS.
- Server-side TCP connection to the requested destination.
- Versioned and length-bounded tunnel handshake.
- Session state manager, path-candidate selector and bounded retry backoff primitives.
- Ed25519 signed-configuration verification primitive.
- Server component health registry.
- SQLite event logging on both client and server, including connection lifecycle, transport, destination, dial latency, transfer byte counts and failures.
- Bounded asynchronous event queue; dropped events and database write errors are counted and reported at shutdown.
- Unit tests and GitHub Actions test/vet workflow for all four modules.

## Database locations

- Client: `data/client.db` (override with `RAMP_CLIENT_DB_PATH` or `-db`).
- Server: `data/server.db` (override with `RAMP_SERVER_DB_PATH` or `-db`).

Database files are runtime artifacts and are ignored by Git. See [docs/storage.md](docs/storage.md).

## Staged features

QUIC, WebRTC and other pluggable transports; multi-bridge discovery; live path measurement; automatic bridge failover; control-plane distribution; key rotation/revocation; and resumable application transfers are not yet complete. See [docs/roadmap.md](docs/roadmap.md).

## Build and test

Use Go 1.23 or newer. Run each module independently:

```sh
cd protocol && go test ./... && go vet ./...
cd ../client && go test ./... && go vet ./...
cd ../server && go test ./... && go vet ./...
cd ../storage && go test ./... && go vet ./...
```

## Security and operational limitations

- QUIC requires UDP reachability; it is not a fallback when UDP is unavailable.
- TLS does not by itself guarantee resistance to traffic classification or blocking.
- A new bridge cannot transparently continue an arbitrary existing TCP connection. Only application protocols designed for resumption can safely resume transfers.
- Keep the local SOCKS5 listener on loopback and do not expose an unauthenticated open proxy.
- Never commit private keys, certificates containing private material, production tokens or secrets.
- Use established, reviewed cryptographic and pluggable-transport implementations.

See [docs/architecture.md](docs/architecture.md), [docs/threat-model.md](docs/threat-model.md), [docs/testing.md](docs/testing.md), and [docs/roadmap.md](docs/roadmap.md).
