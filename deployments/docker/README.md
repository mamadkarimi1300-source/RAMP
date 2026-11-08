# Docker Laboratory Deployment

This directory is reserved for the reproducible local testbed deployment.

## Target services

- `ramp-client`: built from the existing `client` Go module.
- `ramp-bridge`: built from the existing `server` Go module.
- `destination`: controlled HTTP/TCP test endpoint.
- `netem-router`: isolated transit router with Linux traffic-control capability.
- `collector`: collects host/container and network observations.
- Optional dashboard services can be added after metric names and retention are stable.

## Important routing requirement

A Compose file that merely starts a client, bridge and destination on one shared Docker network is not a network-emulation testbed: traffic may bypass the impairment point.

The intended topology places the client and bridge in separate network zones and makes the emulator the only transit path between them. The bridge-side destination remains reachable from the bridge. Both forward and return routes must traverse the emulator.

The router needs narrowly scoped network-administration capabilities (for example, `NET_ADMIN`) to configure forwarding and traffic control. Avoid `privileged: true` unless a tested host/runtime limitation makes it unavoidable; document any exception.

## Certificate and secret provisioning

Generate a local test CA and a bridge certificate with a SAN matching the client `-server-name`. Mount certificates read-only. Supply a unique lab token through an ignored local env file or secret mechanism. Never commit private keys, generated credentials or real user data.

## Host compatibility

The initial target is Docker Desktop on Windows with a WSL2 Linux backend. Linux traffic shaping and routing behavior must be verified inside the Linux containers/kernel used by Docker Desktop. Do not assume that host-side Windows networking applies the same `tc netem` configuration.

## Readiness checklist

- [ ] Multi-stage Dockerfiles build both Go modules from the repository root without changing module boundaries.
- [ ] Compose creates isolated client and bridge networks.
- [ ] Client-to-bridge forward and return routes traverse the emulator.
- [ ] Destination is reachable only from the bridge-side network.
- [ ] TLS certificate verification succeeds with the lab CA.
- [ ] Wrong CA and wrong token tests fail as expected.
- [ ] A non-zero delay profile measurably changes the client-to-bridge path.
- [ ] Removing impairment restores baseline behavior.
- [ ] RAMP SQLite databases and laboratory run artifacts persist in separate volumes/directories.
- [ ] Shutdown does not silently discard the final experiment manifest.

This deployment is a design specification, not a claim that a runnable Compose environment has already been validated.
