# Deployment notes

The server requires a TLS certificate and a high-entropy shared token. Do not store production secrets in this repository.

For a local test certificate, use OpenSSL to create a private CA and a server certificate with a SAN matching the client's `-server-name`. Keep the CA private key and server private key outside the repository.

Example server invocation:

```sh
export RAMP_TOKEN='replace-with-a-long-random-secret'
go run ./server/cmd/ramp-server -listen :8443 -cert /secure/path/server.crt -key /secure/path/server.key -token "$RAMP_TOKEN"
```

Example client invocation:

```sh
go run ./client/cmd/ramp-client -listen 127.0.0.1:1080 -server bridge.example:8443 -server-name bridge.example -ca /secure/path/ca.crt -token "$RAMP_TOKEN"
```

The local SOCKS5 listener defaults to loopback. Keep it there unless you have added and reviewed local-client authentication and firewall rules.
