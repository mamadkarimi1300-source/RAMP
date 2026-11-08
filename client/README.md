# RAMP Client

The client is an independent Go module. It exposes a loopback SOCKS5 CONNECT listener and forwards each accepted CONNECT request through a TLS-protected RAMP tunnel to the server.

## Run

The server certificate must be trusted by the CA file and include the configured server name in its SAN. Set the shared token in the environment rather than exposing it in shell history or process arguments.

```sh
export RAMP_TOKEN='replace-with-a-long-random-secret'
go run ./cmd/ramp-client -listen 127.0.0.1:1080 -server bridge.example:8443 -server-name bridge.example -ca ../deployments/certs/ca.crt
```

The client creates `data/client.db` by default. Override the path with `RAMP_CLIENT_DB_PATH` or `-db`. The database records local SOCKS5 sessions, selected transport, destination, connection latency, failures and directional byte counts.

Configure applications to use SOCKS5 at `127.0.0.1:1080`.

Current scope: SOCKS5 CONNECT and one TCP/TLS upstream path. UDP ASSOCIATE, BIND, user/password auth on the local SOCKS listener, multi-bridge discovery, QUIC and transparent session migration are not implemented yet.
