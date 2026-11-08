# RAMP Server

The server is an independent Go module. It accepts TLS 1.3 connections, validates the shared access token inside the encrypted channel, and opens a TCP connection to the requested destination.

## Run

Provide a certificate and private key whose SAN matches the client's `-server-name`. Keep the shared token secret and distribute it only to authorized clients.

```sh
export RAMP_TOKEN='replace-with-a-long-random-secret'
go run ./cmd/ramp-server -listen :8443 -cert ./server.crt -key ./server.key
```

The bridge creates `data/server.db` by default. Override the path with `RAMP_SERVER_DB_PATH` or `-db`. The database records accepted sessions, TLS/protocol failures, token rejection, egress connection results, dial latency and directional byte counts. The database is local to this server instance.

Do not expose this service without firewall policy, rate limits and operational monitoring. The current server is a single-bridge TCP egress baseline; it is not yet a distributed bridge registry or production deployment.
