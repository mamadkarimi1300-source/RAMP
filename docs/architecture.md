# RAMP Architecture

## System boundary

RAMP separates the user-side client from the remote server. The client accepts local application traffic through SOCKS5 and creates one authenticated TLS tunnel per CONNECT request. The server terminates TLS, validates the shared token, and opens the destination TCP connection.

```text
Application
    |
    | SOCKS5 CONNECT
    v
Client / SOCKS5 Ingress
    |
    | TLS 1.3 + versioned RAMP handshake
    v
Bridge Server
    |
    | destination TCP connection
    v
Internet Destination
```

## Independent deployables

- `client/`: local ingress, TLS tunnel dialer, access selection contracts, measurement types, session lifecycle and recovery primitives.
- `server/`: TLS bridge, token validation, egress connector and health registry.
- `protocol/`: versioned handshake shared by both deployables.
- `storage/`: shared event model, asynchronous writer and SQLite repository used locally by each deployable.

Client and server are separate Go modules. The root workspace is for local development only. Storage is a shared code module, not a central database service.

## Data plane and control plane

The data plane carries application bytes. The control plane supplies bridge candidates, signed configuration and policy. The current baseline contains the client-side Ed25519 configuration verifier and selection/session interfaces; a remote discovery/control service is not yet implemented.

## Transport and bridge selection

These are separate decisions:

1. Bridge selection chooses a reachable server endpoint.
2. Transport selection chooses the protocol used to reach that endpoint.

The current operational transport is TCP + TLS 1.3. QUIC/WebRTC adapters and multi-bridge discovery are roadmap items, not implemented capabilities.

## Session and recovery semantics

Session states are explicit: new, connecting, active, degraded, recovering and closed. The recovery package currently provides bounded exponential backoff only. It does not migrate an existing TCP stream between servers.

A generic TCP connection cannot be continued on a new bridge merely by reusing a session identifier. Transfer resume requires an application protocol with offsets, acknowledgements and durable state, or a shared stateful gateway.

## Measurement and selection

Candidates expose availability, RTT, throughput and recent failures. The current selector is a small deterministic baseline and is not yet fed by a live measurement loop. Before production use, it needs controlled probing, rolling statistics, hysteresis, retry budgets and real multi-network evaluation.

## Observability and persistence

Each client and bridge process owns a separate SQLite database. Event records include session lifecycle, destination, transport/network labels, connection timing, errors and final byte counters. A bounded asynchronous queue keeps database writes off the network forwarding path. Queue overflow and database write failures are counted and reported at shutdown.

The event store is not yet connected to the selector or measurement engine. It does not calculate throughput, drive adaptive decisions, expose a query API or provide retention/rotation. Client/server session IDs are local to each process; end-to-end correlation requires a future protocol correlation identifier.

## Current request flow

1. An application sends a SOCKS5 greeting and CONNECT request to the local client.
2. The client records the accepted local session and validates the SOCKS5 request.
3. The client establishes TLS 1.3 with certificate and server-name validation.
4. The client sends the versioned RAMP open request and shared token inside TLS.
5. The server records the incoming tunnel, validates the request and token, then opens a TCP connection to the destination.
6. The server reports success and both sides relay bytes bidirectionally.
7. Client and server independently persist final directional byte counters and connection lifecycle events.

The destination hostname is sent to the server for resolution there; the client does not perform a local DNS lookup for domain-form SOCKS requests.
